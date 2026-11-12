"""Outline hygiene in the built font (category C, scope "outline").

Source-level checks (fractional coordinates, nodes on extremes) usually run on
.glyphs or .ufo files; these are their binary counterparts, so a delivery can be checked without its source. They run once
per distinct glyf/CFF table and look at a glyph's own contours only: a
component's outlines are checked in the component glyph itself.

Extrema tolerance is 0.5 unit for cubic CFF outlines. TrueType
quadratics converted from cubics bulge by a fraction of a unit between implied
on-curve points, so 1 unit is used there; only real missing extremes show.
"""

import math

from fontTools.pens.basePen import decomposeQuadraticSegment

from . import Hit, check, sfnt
from ..fontview import glyph_label


def _contours(view, name):
    contour = []
    for op, args in view.recording(name):
        if op == "moveTo":
            contour = [(op, args)]
        elif op in ("closePath", "endPath"):
            if contour:
                yield contour
            contour = []
        elif op == "addComponent":
            continue
        else:
            contour.append((op, args))
    if contour:
        yield contour


def _quads(cur, pts):
    for off, on in (decomposeQuadraticSegment(pts) if len(pts) > 2 else [tuple(pts)]):
        yield "quad", (cur, off, on)
        cur = on


def _segments(contour):
    """(kind, points) with absolute start point; kind is 'line', 'cubic' or 'quad'."""
    op, args = contour[0]
    if op == "qCurveTo" and args[-1] is None:
        # a TrueType contour made only of off-curve points: every on-curve is implied
        offs = list(args[:-1])
        start = ((offs[-1][0] + offs[0][0]) / 2, (offs[-1][1] + offs[0][1]) / 2)
        yield from _quads(start, offs + [start])
        return
    start = cur = args[0]
    for op, args in contour[1:]:
        if op == "lineTo":
            yield "line", (cur, args[0])
            cur = args[0]
        elif op == "curveTo":
            yield "cubic", (cur,) + tuple(args)
            cur = args[-1]
        elif op == "qCurveTo":
            pts = list(args)
            for seg in _quads(cur, pts):
                yield seg
            cur = pts[-1]
    if cur != start:
        yield "line", (cur, start)


def _extremum_overshoot(kind, pts):
    """Largest distance by which the curve leaves its endpoints' range on x or y."""
    worst = 0.0
    for axis in (0, 1):
        vals = [p[axis] for p in pts]
        lo, hi = min(vals[0], vals[-1]), max(vals[0], vals[-1])
        ts = []
        if kind == "cubic":
            p0, p1, p2, p3 = vals
            a, b, c = p3 - 3 * p2 + 3 * p1 - p0, 2 * (p2 - 2 * p1 + p0), p1 - p0
            if abs(a) < 1e-9:
                if abs(b) > 1e-9:
                    ts.append(-c / b)
            else:
                d = b * b - 4 * a * c
                if d >= 0:
                    ts += [(-b + d ** 0.5) / (2 * a), (-b - d ** 0.5) / (2 * a)]
        elif kind == "quad":
            p0, p1, p2 = vals
            den = p0 - 2 * p1 + p2
            if abs(den) > 1e-9:
                ts.append((p0 - p1) / den)
        for t in ts:
            if 0.001 < t < 0.999:
                if kind == "cubic":
                    mt = 1 - t
                    e = mt ** 3 * p0 + 3 * mt * mt * t * p1 + 3 * mt * t * t * p2 + t ** 3 * p3
                else:
                    mt = 1 - t
                    e = mt * mt * p0 + 2 * mt * t * p1 + t * t * p2
                worst = max(worst, e - hi, lo - e)
    return worst


@check(id="outline.zero_length", category="C", scope="outline", applies=sfnt,
       title="No zero-length segments or contours",
       classification="Outlines / Hygiene / Zero-length segments",
       what="no segment ends where it starts and no contour collapses to a point or a line "
            "(TrueType: no point repeated on its contour)",
       basis="Node hygiene: rasterizers and hinting tools may mis-handle degenerate segments "
             "(usually harmless).",
       fix="Delete the duplicate nodes in the source.", severity="low")
def zero_length(v):
    hits = []
    glyf = v.font["glyf"] if v.facts.get("outline") == "glyf" else None
    for name in v.glyph_order:
        n = _zero_glyf(glyf, name) if glyf is not None else _zero_pen(v, name)
        if n:
            hits.append(f"{glyph_label(v, name)} ×{n}")
    if hits:
        yield Hit(key="zero-length segments", measured=f"{len(hits)} glyphs", expected="none",
                  glyphs=hits, summary=f"{len(hits)} glyphs have zero-length segments or degenerate contours")


def _zero_glyf(glyf, name):
    """Repeated points (on or off curve) and contours with fewer than 3 distinct points."""
    g = glyf[name]
    if g.numberOfContours <= 0:
        return 0
    coords, ends, _ = g.getCoordinates(glyf)
    n, start = 0, 0
    for end in ends:
        pts = list(coords[start:end + 1])
        start = end + 1
        if len(set(pts)) < 3:
            n += 1
            continue
        n += sum(1 for a, b in zip(pts, pts[1:] + pts[:1]) if a == b)
    return n


def _zero_pen(v, name):
    n = 0
    for contour in _contours(v, name):
        segs = list(_segments(contour))
        pts = {p for _, seg in segs for p in seg}
        if len(pts) <= 1:
            n += 1
            continue
        n += sum(1 for _, seg in segs if len(set(seg)) == 1)
    return n


@check(id="outline.extrema", category="C", scope="outline", applies=sfnt,
       title="Nodes on extremes",
       classification="Outlines / Hygiene / Extremes inside curves",
       what="no curve leaves the range of its end nodes horizontally or vertically by more than the "
            "tolerance (0.5 unit for CFF, 1 unit for TrueType)",
       basis="Horizontal and vertical extremes belong on nodes, in italics too; hinting, "
             "bounding boxes and overlap removal rely on it. Ornaments may skip them on purpose, "
             "and some foundries put italic nodes on slanted extremes — those glyphs are marked.",
       fix="Add nodes at the extremes in the source (Extremes: Balanced or Exact).", severity="low", action="confirm")
def extrema(v):
    tol = 1.0 if v.facts.get("outline") == "glyf" else 0.5
    k = math.tan(math.radians(v.style.get("italic_angle") or 0))
    hits, slanted_only = [], 0
    for name in v.glyph_order:
        worst, count, worst_slanted = 0.0, 0, 0.0
        for contour in _contours(v, name):
            for kind, seg in _segments(contour):
                if kind == "line":
                    continue
                out = _extremum_overshoot(kind, seg)
                if out > tol:
                    count += 1
                    worst = max(worst, out)
                if k:  # the same segment with the italic slant removed
                    worst_slanted = max(worst_slanted, _extremum_overshoot(kind, tuple((x + y * k, y) for x, y in seg)))
        if count:
            mark = ""
            if k and worst_slanted <= tol:
                slanted_only += 1
                mark = " — nodes on slanted extremes"
            hits.append((worst, f"{glyph_label(v, name)}: {count} × up to {worst:.1f}{mark}"))
    if hits:
        hits.sort(reverse=True)
        big = sum(1 for w, _ in hits if w >= 10)
        note = f"; {slanted_only} with nodes on slanted extremes" if slanted_only else ""
        yield Hit(key="extremes inside curves", measured=f"{len(hits)} glyphs ({big} by 10+ units{note})",
                  expected=f"overshoot ≤ {tol}", glyphs=[h for _, h in hits],
                  summary=f"{len(hits)} glyphs have extremes inside curves, {big} of them by 10 units or more",
                  severity="medium" if big else None)


@check(id="outline.fractional", category="C", scope="outline", applies=lambda v: v.facts.get("outline") in ("CFF", "CFF2"),
       title="Integer coordinates in CFF outlines",
       classification="Outlines / Hygiene / Fractional coordinates",
       what="CFF charstrings contain only whole-unit coordinates",
       basis="Fractional points come from scaling or interpolation and round differently per app; "
             "TrueType rounds at export, CFF keeps them.",
       fix="Round coordinates in the source (Round Coordinates and Metrics) and export again.", severity="low")
def fractional(v):
    hits = []
    for name in v.glyph_order:
        n = sum(1 for op, args in v.recording(name) if op not in ("addComponent", "closePath", "endPath")
                for p in args if p is not None and (p[0] != int(p[0]) or p[1] != int(p[1])))
        if n:
            hits.append(f"{glyph_label(v, name)} ×{n}")
    if hits:
        yield Hit(key="fractional coordinates", measured=f"{len(hits)} glyphs", expected="integers",
                  glyphs=hits, summary=f"{len(hits)} glyphs have fractional coordinates")
