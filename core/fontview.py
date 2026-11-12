"""One font as the checks see it: its facts plus lazy access to the tables.

Inventory facts answer most questions (names, metrics, coverage) and are cheap.
Some checks need more: every glyph's width, outlines, GPOS subtables. A
FontView opens the TTFont only when such a check asks, and caches what it
computes, so ten checks reading widths parse hmtx once.

`outline_key` lets outline checks run once per distinct outline table: the App,
Desktop and Web builds of one style usually carry identical glyf/CFF data, and
reporting a zero-length contour 4 times is noise. Findings still list every
file that shares the outlines.
"""

import hashlib
import io
import unicodedata

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

WHITESPACE = {0x0009, 0x000A, 0x000D, 0x0020, 0x00A0, 0x1680, 0x180E, 0x2028, 0x2029,
              0x202F, 0x205F, 0x3000, 0xFEFF} | set(range(0x2000, 0x200F)) | set(range(0x2060, 0x2065))


def is_blank_codepoint(cp):
    """Characters that are allowed (or expected) to have no outline."""
    if cp in WHITESPACE:
        return True
    return unicodedata.category(chr(cp)) in ("Zs", "Zl", "Zp", "Cc", "Cf")


class FontView:
    def __init__(self, path, facts):
        self.path = path              # absolute path on disk (or in Pyodide's FS)
        self.facts = facts            # the inventory facts, including "path" (relative)
        self.rel = facts["path"]
        self.ctx_ots = None           # OTS verdict from the browser or the ots module
        self._font = None
        self._cache = {}

    # ---------------------------------------------------------------- basics
    @property
    def ok(self):
        return "error" not in self.facts

    @property
    def font(self):
        if self._font is None:
            with open(self.path, "rb") as fh:
                self._font = TTFont(io.BytesIO(fh.read()), lazy=True)
        return self._font

    def release(self):
        """Drop the parsed tables, keep the light caches (cmap, widths, glyph order).

        The engine visits one font at a time and calls this afterwards, so a
        delivery of 100 CJK fonts never holds more than one parsed font.
        """
        self._font = None
        for k in [k for k in self._cache if k == "glyphset" or (isinstance(k, tuple) and k[0] in ("bounds", "rec"))]:
            del self._cache[k]

    @property
    def style(self):
        return self.facts.get("style", {})

    @property
    def names(self):
        return self.facts.get("names", {}).get("windows", {})

    @property
    def family(self):
        return self.style.get("family") or "?"

    @property
    def subfamily(self):
        return self.style.get("subfamily") or "?"

    @property
    def fmt(self):
        return self.facts.get("format")

    @property
    def lineage(self):
        return self.facts.get("lineage")

    @property
    def variable(self):
        return bool(self.facts.get("variation"))

    @property
    def italic(self):
        return "ITALIC" in (self.style.get("fs_selection") or [])

    @property
    def is_sfnt(self):
        return self.fmt in ("TTF", "OTF")

    def label(self):
        return f"{self.family} {self.subfamily}"

    # ---------------------------------------------------------------- tables
    def _memo(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    @property
    def cmap(self):
        return self._memo("cmap", lambda: self.font.getBestCmap() or {})

    @property
    def glyph_order(self):
        return self._memo("order", self.font.getGlyphOrder)

    @property
    def widths(self):
        """glyph name -> advance width (default master for variable fonts)."""
        return self._memo("widths", lambda: {g: m[0] for g, m in self.font["hmtx"].metrics.items()})

    @property
    def glyph_set(self):
        return self._memo("glyphset", self.font.getGlyphSet)

    def recording(self, name):
        """The glyph's own drawing operations (components not decomposed), recorded once."""
        def compute():
            pen = RecordingPen()
            self.glyph_set[name].draw(pen)
            return pen.value
        return self._memo(("rec", name), compute)

    def bounds(self, name):
        """(xMin, yMin, xMax, yMax) of a glyph's outline, or None when empty.

        Shared between all files with the same outline key, so the Web and App
        copies of a style reuse what the Desktop copy computed.
        """
        key = (self.outline_key, name)
        if key not in SHARED_BOUNDS:
            pen = BoundsPen(self.glyph_set)
            self.glyph_set[name].draw(pen)
            SHARED_BOUNDS[key] = pen.bounds
        return SHARED_BOUNDS[key]

    def char_of(self, name):
        """First codepoint mapped to a glyph name, for readable reports."""
        rev = self._memo("rev", lambda: _reverse(self.cmap))
        return rev.get(name)

    @property
    def exact_outline_key(self):
        """Hash of the raw glyf+loca or CFF table — cheap for TTF, OTF and WOFF.

        WOFF2 stores glyf transformed; rebuilding it costs about half a second per
        font, so WOFF2 gets None here and is matched by `derived_outline_key`.
        """
        def compute():
            if self.fmt == "WOFF2":
                return None
            tag = next((t for t in ("CFF2", "CFF ", "glyf") if t in self.font.reader), None)
            if tag is None:
                return f"none:{self.facts.get('sha256')}"
            h = hashlib.sha256(self.font.reader[tag])
            if tag == "glyf" and "loca" in self.font.reader:
                h.update(self.font.reader["loca"])
            return f"{tag.strip()}:{h.hexdigest()[:16]}"
        return self._memo("exact_key", compute)

    @property
    def derived_outline_key(self):
        """Glyph order, advance widths and cmap: identical for all copies of one style."""
        def compute():
            h = hashlib.sha256()
            h.update("\n".join(self.glyph_order).encode())
            h.update(repr(sorted(self.font["hmtx"].metrics.items())).encode())
            h.update(repr(sorted(self.cmap.items())).encode())
            return h.hexdigest()[:16]
        return self._memo("derived_key", compute)

    @property
    def outline_key(self):
        return self._cache.get("outline_key") or self.exact_outline_key or f"woff2:{self.derived_outline_key}"


SHARED_BOUNDS = {}


def assign_outline_keys(views):
    """Give every view the key of the outline table it shares with others.

    TTF, OTF and WOFF are keyed by their raw outline bytes. A WOFF2 takes the
    key of a TTF/OTF/WOFF with the same glyph order, widths and cmap — the same
    style exported to another container — and only gets its own key (and its
    own outline checks) when there is no such sibling.
    """
    SHARED_BOUNDS.clear()
    by_derived = {}
    for v in views:
        if v.ok and v.fmt != "WOFF2":
            v._cache["outline_key"] = v.exact_outline_key
            by_derived.setdefault(v.derived_outline_key, v.exact_outline_key)
    for v in views:
        if v.ok and v.fmt == "WOFF2":
            v._cache["outline_key"] = by_derived.get(v.derived_outline_key) or f"woff2:{v.derived_outline_key}"


def _reverse(cmap):
    rev = {}
    for cp, name in sorted(cmap.items()):
        rev.setdefault(name, cp)
    return rev


def glyph_label(view, name):
    """'eacute (U+00E9 é)' — the form glyphs are listed in findings."""
    cp = view.char_of(name)
    if cp is None:
        return name
    ch = chr(cp)
    shown = ch if unicodedata.category(ch)[0] not in "CZM" else ""
    return f"{name} (U+{cp:04X}{' ' + shown if shown else ''})"
