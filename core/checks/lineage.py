"""Lineages and formats of one style agree (category F).

A delivery often carries one style several times: Desktop TTF, App TTF, Web
WOFF and WOFF2. What may differ between them is decided per client (names,
fsType, hinting, a legacy kern table, glyph names in post); what must not
differ is the design: the glyph set, the cmap, advance widths, outlines, the
layout tables and the vertical metrics. A QA vendor may verify "lineage consistency" by machine; this is the generic
part of that, without a client table.

Copies are paired by file name with the lineage marker removed
(AcmeSans_A_Bd, AcmeSans_W_Bd and AcmeSans_Bd are one style), because
web fonts often have obfuscated names and cannot be paired by name ID.
"""

import hashlib
import os
import re
from collections import defaultdict

from . import Hit, check

MARKER = re.compile(r"(?i)(?<=[_\-\s])(a|w|d|app|web|desktop)(?=[_\-\s]|$)")


def style_key(rel):
    stem = os.path.splitext(os.path.basename(rel))[0]
    stem = MARKER.sub("", stem)
    return re.sub(r"[_\-\s]+", "_", stem).strip("_").lower()


def _digest(data):
    return hashlib.sha256(data).hexdigest()[:12]


def _sfnt_bytes(v):
    """HarfBuzz reads sfnt only: decompress WOFF/WOFF2 through fontTools."""
    import io
    from fontTools.ttLib import TTFont
    with open(v.path, "rb") as fh:
        data = fh.read()
    if v.fmt in ("WOFF", "WOFF2"):
        font = TTFont(io.BytesIO(data))
        font.flavor = None
        out = io.BytesIO()
        font.save(out, reorderTables=False)
        data = out.getvalue()
    return data


def _shape_all(v, texts, feature_tags):
    """texts: (default text, per-feature text) — kerning pairs only matter once."""
    import uharfbuzz as hb
    from ..hbshim import rows
    font = hb.Font(hb.Face(hb.Blob(_sfnt_bytes(v))))
    result = {}
    for tag in [None] + feature_tags:
        buf = hb.Buffer()
        buf.add_str(texts[0] if tag is None else texts[1])
        buf.guess_segment_properties()
        hb.shape(font, buf, {tag: True} if tag else {})
        result[tag or "default"] = _digest(repr([(g, cl, ax, dx, dy) for g, cl, ax, _, dx, dy in rows(buf)]).encode())
    v.release()
    return result


def _layout_behaviour(ref, odd):
    """Copies whose shaping differs from the reference, and the features where it does."""
    from .variable import _kern_text
    chars = "".join(chr(c) for c in sorted(ref.cmap) if c > 0x20 and not 0xD800 <= c <= 0xDFFF)
    texts = (_kern_text() + " " + chars, chars)
    tags = sorted(set(((ref.facts.get("layout") or {}).get("GSUB") or {}).get("features", [])) - {"aalt"})
    want = _shape_all(ref, texts, tags)
    bad, feats = [], set()
    for v in odd:
        got = _shape_all(v, texts, tags)
        diff = [t for t in want if got.get(t) != want[t]]
        if diff:
            bad.append(v)
            feats.update(diff)
    return bad, sorted(feats)


def _signature(v):
    font = v.font
    order = v.glyph_order
    index = {g: i for i, g in enumerate(order)}
    sig = {
        "glyph count": len(order),
        "cmap": _digest(repr(sorted((c, index[g]) for c, g in v.cmap.items())).encode()),
        "advance widths": _digest(repr([v.widths.get(g) for g in order]).encode()),
        "vertical metrics": repr((v.facts["metrics"]["upm"], v.facts["metrics"]["hhea"], v.facts["metrics"].get("typo"),
                                  v.facts["metrics"].get("win"),
                                  "USE_TYPO_METRICS" in (v.style.get("fs_selection") or []))),
    }
    sig["layout"] = "|".join(_digest(font.reader[t]) if t in font.reader else "-" for t in ("GSUB", "GPOS", "GDEF"))
    if v.fmt != "WOFF2":  # WOFF2 outlines are matched through the derived key, see fontview
        sig["outlines"] = v.outline_key
    widths = [v.widths.get(g) for g in order]
    v.release()
    return sig, widths, order


@check(id="lineage.copies_agree", category="F", scope="package",
       title="Copies of one style agree across lines and formats",
       classification="Lineage differences / Same style / Design data",
       what="Desktop, App and Web copies of a style (TTF, OTF, WOFF, WOFF2) have the same glyph set, cmap, "
            "advance widths, outlines, GSUB/GPOS/GDEF and vertical metrics; names, fsType, hinting, legacy kern "
            "and post may differ by design",
       basis="The same text must set identically in the app, on the desktop and on the web; differences "
             "mean one lineage was built from another source state.",
       fix="Rebuild every lineage from one export; keep only the per-lineage differences the brief asks for.",
       severity="medium",
       symptoms=("Web vs desktop: the same text breaks into lines differently",))
def copies_agree(views, ctx=None):
    groups = defaultdict(list)
    for v in views:
        if v.ok:
            groups[(style_key(v.rel), v.variable)].append(v)
    for (key, _), vs in sorted(groups.items()):
        if len(vs) < 2:
            continue
        # reference copy: a Desktop sfnt if there is one
        vs = sorted(vs, key=lambda v: (v.lineage != "Desktop", not v.is_sfnt, v.rel))
        sigs = {v.rel: _signature(v) for v in vs}
        ref = vs[0]
        rsig, rwidths, rorder = sigs[ref.rel]
        for aspect in rsig:
            odd = [v for v in vs[1:] if aspect in sigs[v.rel][0] and sigs[v.rel][0][aspect] != rsig[aspect]]
            if aspect == "layout" and odd:
                # tables compiled differently can still behave the same: compare what they do
                odd, feats = _layout_behaviour(ref, odd)
                if odd:
                    yield Hit(key="copies differ: layout behaviour", files=[ref.rel] + [v.rel for v in odd],
                              measured=f"{len(odd)} of {len(vs) - 1} copies of “{key}” shape differently from "
                                       f"{os.path.basename(ref.rel)}",
                              expected="same shaping with every feature", glyphs=[f"features: {', '.join(feats)}"],
                              summary="copies of one style shape text differently")
                continue
            if not odd:
                continue
            detail = []
            if aspect == "advance widths":
                for v in odd[:3]:
                    _, w, order = sigs[v.rel]
                    if order == rorder:
                        diff = [f"{g} {a}→{b}" for g, a, b in zip(order, rwidths, w) if a != b]
                        detail.append(f"{os.path.basename(v.rel)}: {len(diff)} glyphs, e.g. " + ", ".join(diff[:5]))
            elif aspect in ("glyph count", "vertical metrics"):
                detail = [f"{os.path.basename(v.rel)}: {sigs[v.rel][0][aspect]}" for v in odd[:4]]
            yield Hit(key=f"copies differ: {aspect}", files=[ref.rel] + [v.rel for v in odd],
                      measured=f"{len(odd)} of {len(vs) - 1} copies of “{key}” differ from {os.path.basename(ref.rel)}",
                      expected=f"same {aspect} as {os.path.basename(ref.rel)}", glyphs=detail,
                      summary=f"copies of one style differ in {aspect}",
                      action="confirm" if aspect in ("GSUB", "GPOS", "GDEF") else None)
