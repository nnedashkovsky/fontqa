"""Character set, glyphs and widths (category C).

Coverage itself (Adobe Latin 1–5 per style) is not an issue and goes to the
Coverage sheet; the checks here are about consistency and about glyphs that
would misbehave: a mapped character with no outline, marks with width, spaces
of different widths, and widths that differ by a unit or two between weights —
the ◆ 1001 vs 1000 case in RT's report.
"""

import json
import os
import unicodedata
from collections import Counter, defaultdict

from . import Hit, check, families, files_of, sfnt, static
from ..fontview import glyph_label, is_blank_codepoint

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CHARSETS = None
CURRENCIES = (0x24, 0x20AC, 0xA3, 0xA5, 0xA2)


def charsets():
    global _CHARSETS
    if _CHARSETS is None:
        with open(os.path.join(DATA, "charsets.json"), encoding="utf-8") as fh:
            _CHARSETS = {k: set(v) for k, v in json.load(fh).items() if not k.startswith("_")}
    return _CHARSETS


def cp_label(cp):
    ch = chr(cp)
    shown = ch if unicodedata.category(ch)[0] not in "CZM" else ""
    return f"U+{cp:04X}{' ' + shown if shown else ''}"


def coverage(view):
    """{charset name: (have, total, missing codepoints)} — for the Coverage sheet."""
    cmap = set(view.cmap)
    return {name: (len(cps & cmap), len(cps), sorted(cps - cmap)) for name, cps in charsets().items()}


@check(id="charset.family_same", category="C", scope="family",
       title="Every style has the same character set",
       classification="Character set / Family / Same codepoints",
       what="within a family and lineage, all styles map the same codepoints",
       basis="Text switches styles mid-paragraph; a missing character falls back to another font. "
             "MyFonts requires identical character sets across a family.",
       fix="Add the missing glyphs to the styles that lack them, or document the difference "
           "(e.g. a Display sub-family with a smaller set).", severity="medium", action="confirm")
def family_same(group):
    if len(group) < 2:
        return
    sets = {v.rel: set(v.cmap) for v in group}
    union = set().union(*sets.values())
    by_missing = defaultdict(list)
    for v in group:
        missing = frozenset(union - sets[v.rel])
        if missing:
            by_missing[missing].append(v)
    for missing, vs in by_missing.items():
        ms = sorted(missing)
        yield Hit(key=f"{len(ms)} codepoints missing in some styles", files=files_of(vs),
                  measured=f"{len(ms)} codepoints the other styles have", expected="same set",
                  glyphs=[cp_label(c) for c in ms[:60]] + (["…"] if len(ms) > 60 else []),
                  summary=f"{len(vs)} styles lack {len(ms)} codepoints present elsewhere in the family")


@check(id="charset.store_minimum", category="C", scope="file", applies=sfnt,
       title="Western European minimum for stores",
       classification="Character set / Store minimum / Western European",
       what="every printable Windows-1252 character, including $ € £ ¥ ¢",
       basis="MyFonts validates a Western European minimum with the five currency signs; "
             "Windows-1252 is the closest public definition.",
       fix="Add the missing characters before submitting to stores.", severity="medium")
def store_minimum(v):
    have = set(v.cmap)
    missing = sorted(charsets()["Western European (cp1252)"] - have)
    if missing:
        cur = [c for c in CURRENCIES if c not in have]
        yield Hit(key=f"Western European set incomplete", measured=f"{len(missing)} missing"
                  + (f", currencies: {' '.join(chr(c) for c in cur)}" if cur else ""),
                  expected="all 218 printable Windows-1252 characters",
                  glyphs=[cp_label(c) for c in missing],
                  summary=f"{len(missing)} Western European characters missing"
                  + (f" (incl. {' '.join(chr(c) for c in cur)})" if cur else ""))


@check(id="glyphs.notdef", category="C", scope="outline", applies=sfnt,
       title=".notdef is first and visible",
       classification="Glyphs / .notdef / Position and outline",
       what="glyph 0 is .notdef and has an outline",
       basis="OpenType spec: glyph 0 is shown for missing characters; an empty one hides them.",
       fix="Keep .notdef first and draw a box in it.", severity="medium")
def notdef(v):
    order = v.glyph_order
    if not order or order[0] != ".notdef":
        yield Hit(key=".notdef not first", measured=order[0] if order else "no glyphs", expected=".notdef",
                  summary=f"glyph 0 is {order[0] if order else 'missing'}")
    elif v.bounds(".notdef") is None:
        yield Hit(key=".notdef empty", measured="no outline", expected="a visible box",
                  summary=".notdef has no outline", severity="low")


@check(id="glyphs.empty_mapped", category="C", scope="outline", applies=sfnt,
       title="Encoded characters have outlines",
       classification="Glyphs / Outlines / Empty glyphs",
       what="every encoded character except spaces and controls has an outline",
       basis="An empty glyph for a visible character prints nothing and blocks fallback to another font.",
       fix="Draw the glyph or remove its Unicode value.", severity="high",
       symptoms=("All applications: typed characters disappear; nothing is printed and no fallback font is used",))
def empty_mapped(v):
    empty = []
    seen = set()
    for cp, name in sorted(v.cmap.items()):
        if name in seen or is_blank_codepoint(cp):
            continue
        seen.add(name)
        if v.bounds(name) is None:
            empty.append(glyph_label(v, name))
    if empty:
        yield Hit(key="encoded glyphs without outline", measured=f"{len(empty)} glyphs", expected="outlines",
                  glyphs=empty, summary=f"{len(empty)} encoded glyphs have no outline")


@check(id="glyphs.spaces", category="C", scope="file", applies=sfnt,
       title="Space widths",
       classification="Glyphs / Spaces / Widths",
       what="space and no-break space are equally wide; zero-width characters have width 0; "
            "figure space equals the zero digit",
       basis="Unicode: U+00A0 is a space of the same width that does not break; U+200B…200D, U+2060, "
             "U+FEFF are zero-width; U+2007 is the width of a tabular digit.",
       fix="Set the widths (or make U+00A0 a component of space).", severity="medium")
def spaces(v):
    w, cmap = v.widths, v.cmap
    if 0x20 in cmap and 0xA0 in cmap and w[cmap[0x20]] != w[cmap[0xA0]]:
        yield Hit(key="no-break space ≠ space", measured=f"space {w[cmap[0x20]]}, nbspace {w[cmap[0xA0]]}",
                  expected="equal", summary=f"space {w[cmap[0x20]]} vs no-break space {w[cmap[0xA0]]}")
    wide = [f"{cp_label(cp)} {w[cmap[cp]]}" for cp in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF)
            if cp in cmap and w[cmap[cp]] != 0]
    if wide:
        yield Hit(key="zero-width characters have width", measured=", ".join(wide), expected="0",
                  summary="zero-width characters have width: " + ", ".join(wide), severity="low")
    if 0x2007 in cmap and 0x30 in cmap:
        from .layout import feature_single_map
        zero = feature_single_map(v.font, "tnum").get(cmap[0x30], cmap[0x30])
        if w[cmap[0x2007]] != w[zero]:
            yield Hit(key="figure space ≠ tabular zero", measured=f"figure space {w[cmap[0x2007]]}, {zero} {w[zero]}",
                      expected=str(w[zero]), summary=f"figure space {w[cmap[0x2007]]} is not as wide as the tabular zero ({w[zero]})",
                      severity="low")


@check(id="glyphs.mark_widths", category="C", scope="file", applies=sfnt,
       title="Combining marks have zero width",
       classification="Glyphs / Marks / Advance width",
       what="combining marks (Unicode Mn) and GDEF mark glyphs have advance width 0",
       basis="A combining mark with width pushes the next letter away when the mark is typed after its base.",
       fix="Set the width of combining marks to 0 (Glyphs: the '*comb' glyphs).", severity="medium",
       symptoms=("All applications: decomposed accents (base + combining mark) leave a gap after the letter",))
def mark_widths(v):
    w = v.widths
    marks = {name for cp, name in v.cmap.items() if unicodedata.category(chr(cp)) == "Mn"}
    if "GDEF" in v.font and v.font["GDEF"].table.GlyphClassDef:
        marks |= {g for g, c in v.font["GDEF"].table.GlyphClassDef.classDefs.items() if c == 3}
    wide = sorted(g for g in marks if w.get(g, 0) != 0)
    if wide:
        yield Hit(key="marks with width", measured=f"{len(wide)} marks", expected="width 0",
                  glyphs=[f"{glyph_label(v, g)} {w[g]}" for g in wide],
                  summary=f"{len(wide)} combining marks have a non-zero width")


@check(id="glyphs.tabular", category="C", scope="file", applies=sfnt,
       title="Tabular figures are tabular",
       classification="Glyphs / Figures / Tabular widths",
       what="with a tnum feature, the figures it produces share one width",
       basis="Tables and prices align only when every tabular figure has the same advance.",
       fix="Give all tabular figures (and their variants) the same width.", severity="medium")
def tabular(v):
    if "tnum" not in ((v.facts.get("layout") or {}).get("GSUB") or {}).get("features", []):
        return
    from .layout import feature_single_map
    digits = [v.cmap[c] for c in range(0x30, 0x3A) if c in v.cmap]
    tnum = feature_single_map(v.font, "tnum")
    outs = [tnum.get(g, g) for g in digits]
    widths = Counter(v.widths[g] for g in outs)
    if len(widths) > 1:
        yield Hit(key="tnum figures differ in width", measured=", ".join(f"{w}×{n}" for w, n in widths.items()),
                  expected="one width", glyphs=[f"{g} {v.widths[g]}" for g in outs],
                  summary="figures produced by tnum have different widths")


@check(id="widths.near_equal", category="C", scope="family", applies=static,
       title="Widths that should match across styles differ by a unit or two",
       classification="Character widths / Family / Near-equal widths",
       what="a glyph whose width is the same in most styles is not off by 1–2 units in a few",
       basis="Such widths are almost always meant to be equal (fixed-width symbols, tabular figures); "
             "A typical case: ◆◇ at 1001 instead of 1000 in some weights.",
       fix="Set the odd widths to the common value in the source.", severity="medium")
def near_equal(group):
    for italic in (False, True):
        yield from _near_equal([v for v in group if sfnt(v) and not v.variable and v.italic == italic])


def _style_label(v):
    sub = v.subfamily
    return sub if len(sub) > 1 and sub.isprintable() else os.path.basename(v.rel)


def _near_equal(group):
    if len(group) < 3:
        return
    common_names = set.intersection(*(set(v.widths) for v in group))
    odd_files, glyphs = set(), []
    for name in sorted(common_names):
        vals = Counter(v.widths[name] for v in group)
        if len(vals) == 1 or max(vals) - min(vals) > 2:
            continue
        # the expected width: the most common one; on a tie, the rounder number (1000 over 1001)
        top = max(vals, key=lambda w: (vals[w], w % 10 == 0, w % 2 == 0, -w))
        n = vals[top]
        if n < 0.4 * len(group):
            continue
        bad = [v for v in group if v.widths[name] != top]
        odd_files.update(v.rel for v in bad)
        glyphs.append(f"{glyph_label(group[0], name)}: {top} in {n}, " +
                      ", ".join(f"{v.widths[name]} in {_style_label(v)}" for v in bad[:8]) +
                      (f" … ({len(bad)} styles)" if len(bad) > 8 else ""))
    if glyphs:
        yield Hit(key="widths off by 1–2 units", files=sorted(odd_files), measured=f"{len(glyphs)} glyphs",
                  expected="the common width", glyphs=glyphs,
                  summary=f"{len(glyphs)} glyphs are 1–2 units off the width they have in the other styles")
