"""Variable fonts (category G).

Three kinds of checks. Structure: the default instance carries name ID 2/17
and no other instance does (RT P-03), instance names are unique, STAT describes
every axis and every named instance, HVAR is there. Interpolation: fontTools'
varLib.interpolatable compares the masters stored in gvar/CFF2 (the warnings RT
counted as P-33). Agreement with the statics of the same delivery: each named
instance is read in place (getGlyphSet with a location, no full instancing)
and compared with the static font of the same style — widths, outlines and,
through HarfBuzz, the spacing of every pair of printable ASCII characters
(RT's E-12: twelve pairs kerned in the statics and not in the VF).
"""

import json
import os
import tempfile
from collections import Counter, defaultdict

from fontTools.pens.boundsPen import BoundsPen

from . import Hit, check, files_of, installable
from ..fontview import glyph_label

KERN_ALPHABET = [chr(c) for c in range(0x20, 0x7F)]
LAYOUT_OFF = {"liga": False, "clig": False, "dlig": False, "calt": False, "rlig": False, "rclt": False}


def variable(v):
    return v.ok and v.variable


def installable_variable(v):
    """Instance names matter where the font is installed; web fonts may carry obfuscated names."""
    return variable(v) and installable(v)


def _name(font, nid):
    if nid in (None, 0xFFFF):
        return None
    return font["name"].getDebugName(nid)


def _default_location(font):
    return {a.axisTag: a.defaultValue for a in font["fvar"].axes}


# ------------------------------------------------------------------ structure

@check(id="vf.default_instance", category="G", scope="file", applies=installable_variable,
       title="The default instance owns name ID 2/17",
       classification="Variable font / Named instances / Default instance name",
       what="the named instance at the default location carries the name of ID 17 (or ID 2) — through ID 2/17 "
            "itself or another ID with the same text; no other instance uses ID 2 or 17",
       basis="OpenType fvar: the default instance is named like name ID 2/17, other instances not "
             "(e.g. default Light while ID 2 says Regular).",
       fix="Either move the default location to the instance ID 2/17 names (usually Regular), or give the "
           "default instance ID 17 with its own name and point the other instance to a new name ID.",
       severity="medium",
       symptoms=("macOS Font Book, TextEdit: the instance list shows a duplicate Regular and misses the default style",))
def default_instance(v):
    font = v.font
    default = _default_location(font)
    style = v.names.get("17") or v.names.get("2")
    at_default = [i for i in font["fvar"].instances
                  if all(abs(i.coordinates.get(t, d) - d) < 1e-6 for t, d in default.items())]
    if not at_default:
        yield Hit(key="no named instance at the default location", measured=f"default {default}",
                  expected="a named instance at the default", summary="no named instance sits at the default location",
                  action="confirm", severity="low")
    else:
        inst = at_default[0]
        name = _name(font, inst.subfamilyNameID)
        if name != style:
            yield Hit(key="default instance not named by ID 2/17",
                      measured=f"default instance “{name}” (name ID {inst.subfamilyNameID}); ID 2/17 says “{style}”",
                      expected=f"default instance uses ID 2 or 17 (“{style}”)",
                      summary=f"the default instance is “{name}”, but name ID 2/17 says “{style}”")
    others = [i for i in font["fvar"].instances if i not in at_default and i.subfamilyNameID in (2, 17)]
    if others:
        shown = ", ".join(f"“{_name(font, i.subfamilyNameID)}” at {dict(i.coordinates)}" for i in others[:4])
        yield Hit(key="non-default instance uses ID 2/17", measured=shown, expected="IDs 2/17 only for the default",
                  summary=f"{len(others)} non-default instances use name ID 2 or 17")


@check(id="vf.instance_names", category="G", scope="file", applies=installable_variable,
       title="Named instances have unique names",
       classification="Variable font / Named instances / Duplicate names",
       what="no two named instances share a subfamily name or a PostScript name",
       basis="Font menus list instances by name; duplicates show twice and write the same name into documents.",
       fix="Rename the duplicate instances in the source.", severity="medium",
       symptoms=("Font menus: the same style name appears twice",))
def instance_names(v):
    font = v.font
    subs = Counter(_name(font, i.subfamilyNameID) for i in font["fvar"].instances)
    pss = Counter(_name(font, i.postscriptNameID) for i in font["fvar"].instances if i.postscriptNameID not in (None, 0xFFFF))
    dup = [n for n, c in subs.items() if c > 1]
    duppa = [n for n, c in pss.items() if c > 1]
    if dup:
        yield Hit(key="duplicate instance names", measured=", ".join(f"“{n}” × {subs[n]}" for n in dup),
                  expected="unique", summary="instance names repeat: " + ", ".join(dup))
    if duppa:
        yield Hit(key="duplicate instance PostScript names", measured=", ".join(duppa), expected="unique",
                  summary="instance PostScript names repeat: " + ", ".join(duppa))


@check(id="vf.stat", category="G", scope="file", applies=variable,
       title="STAT describes the axes and the instances",
       classification="Variable font / STAT / Axes and axis values",
       what="STAT exists, lists every fvar axis, has an ElidedFallbackNameID that resolves, and has an axis "
            "value for every coordinate a named instance uses",
       basis="OpenType STAT; Windows and Office build style names from STAT, CSS and newer apps rely on it.",
       fix="Add STAT axis values (Glyphs: axis locations / STAT settings) for every instance coordinate.",
       severity="medium")
def stat(v):
    font = v.font
    if "STAT" not in font:
        yield Hit(key="no STAT table", measured="missing", expected="STAT", summary="variable font without STAT")
        return
    st = font["STAT"].table
    tags = [a.AxisTag for a in (st.DesignAxisRecord.Axis if st.DesignAxisRecord else [])]
    missing_axes = [a.axisTag for a in font["fvar"].axes if a.axisTag not in tags]
    if missing_axes:
        yield Hit(key="fvar axes missing from STAT", measured=", ".join(missing_axes), expected="all fvar axes",
                  summary="STAT lacks axes " + ", ".join(missing_axes))
    efn = getattr(st, "ElidedFallbackNameID", None)
    if efn is None or _name(font, efn) is None:
        yield Hit(key="no ElidedFallbackNameID", measured=str(efn), expected="a name ID that exists",
                  summary="STAT has no usable ElidedFallbackNameID", severity="low")
    values = defaultdict(list)  # axis tag -> list of (lo, hi)
    for av in (st.AxisValueArray.AxisValue if st.AxisValueArray else []):
        if av.Format in (1, 3):
            values[tags[av.AxisIndex]].append((av.Value, av.Value))
        elif av.Format == 2:
            values[tags[av.AxisIndex]].append((av.RangeMinValue, av.RangeMaxValue))
        elif av.Format == 4:
            for rec in av.AxisValueRecord:
                values[tags[rec.AxisIndex]].append((rec.Value, rec.Value))
    uncovered = set()
    for inst in font["fvar"].instances:
        for tag, val in inst.coordinates.items():
            if not any(lo - 1e-6 <= val <= hi + 1e-6 for lo, hi in values.get(tag, [])):
                uncovered.add(f"{tag}={val:g}")
    if uncovered:
        yield Hit(key="instance coordinates without axis values", measured=", ".join(sorted(uncovered)),
                  expected="an axis value per coordinate", action="confirm",
                  summary=f"{len(uncovered)} instance coordinates have no STAT axis value")


@check(id="vf.var_tables", category="G", scope="file", applies=variable,
       title="Variation tables for metrics",
       classification="Variable font / Variation tables / HVAR, VVAR",
       what="HVAR exists; HVAR side-bearing maps and VVAR (for fonts with vertical metrics) are reported",
       basis="OpenType HVAR (recommended): without it apps must run gvar to get advances; LSB/RSB maps and VVAR "
             "are recommended too, but their absence is usually harmless.",
       fix="Let the export build HVAR (and VVAR for vertical fonts).", severity="low", action="ok")
def var_tables(v):
    font = v.font
    if "gvar" in font and "HVAR" not in font:
        yield Hit(key="no HVAR", measured="missing", expected="HVAR", summary="no HVAR: advances come from gvar only",
                  action="confirm", severity="medium")
    elif "HVAR" in font:
        hv = font["HVAR"].table
        if not getattr(hv, "LsbMap", None) and not getattr(hv, "RsbMap", None):
            yield Hit(key="HVAR without side-bearing maps", measured="advance map only", expected="LSB/RSB maps",
                      summary="HVAR holds advance deltas only (no LSB/RSB maps)")
    if "vmtx" in font and "VVAR" not in font:
        yield Hit(key="no VVAR", measured="vmtx without VVAR", expected="VVAR",
                  summary="vertical metrics without VVAR")


# ------------------------------------------------------------------ interpolation

@check(id="vf.interpolation", category="G", scope="outline", applies=variable,
       title="Masters interpolate cleanly",
       classification="Variable font / Interpolation / Master compatibility",
       what="fontTools varLib.interpolatable finds no contour-order, start-point, weight or kink problems "
            "between the masters stored in the font",
       basis="Problems between masters show as twisted or thinning shapes at intermediate locations "
             "(often many glyphs with no visible breakage).",
       fix="Look at the listed glyphs at intermediate locations; fix contour order and start points in the source.",
       severity="low", action="confirm")
def interpolation(v):
    from fontTools.varLib import interpolatable
    glyphs = _interpolation_sample(v)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "interp.json")
        args = [v.path, "--json", "--output", out]
        if glyphs is not None:
            args[1:1] = ["--glyphs", " ".join(glyphs)]
        # with numpy installed the contour matcher returns numpy integers, which
        # interpolatable's own json.dumps cannot write; serialise them as plain numbers
        dumps = json.dumps
        json.dumps = lambda obj, **kw: dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o), **kw)
        try:
            interpolatable.main(args)
        except SystemExit:
            pass
        finally:
            json.dumps = dumps
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            return
        with open(out, encoding="utf-8") as fh:
            problems = json.load(fh)
    if not problems:
        return
    kinds = Counter()
    per_kind = defaultdict(list)
    for glyph, ps in sorted(problems.items()):
        for t in sorted({p["type"] for p in ps}):
            kinds[t] += 1
            per_kind[t].append(glyph)
    shown = [f"{t}: " + ", ".join(glyph_label(v, g) for g in gs[:12]) + (f" … ({len(gs)})" if len(gs) > 12 else "")
             for t, gs in sorted(per_kind.items())]
    sampled = f" ({len(glyphs)} of {len(v.glyph_order)} glyphs checked)" if glyphs is not None else ""
    yield Hit(key="interpolation warnings", measured=f"{len(problems)} glyphs{sampled}: " + ", ".join(f"{t} {n}" for t, n in kinds.most_common()),
              expected="none", glyphs=shown,
              summary=f"{len(problems)} glyphs have interpolation warnings between masters")


INTERPOLATION_SAMPLE = 800  # about a minute on CJK glyphs in the terminal


def _interpolation_sample(v):
    """All glyphs of a Latin-sized font; for big fonts the glyphs below U+3000 plus an even spread.

    interpolatable matches contours across every master; on 28 780 glyphs and 11 masters
    that is far more than an hour, and impossible in the browser. The sample keeps the
    finding honest: it says how many glyphs were checked.
    """
    order = v.glyph_order
    if len(order) <= INTERPOLATION_SAMPLE:
        return None
    low = {v.cmap[c] for c in v.cmap if c < 0x3000}
    keep = [g for g in order if g in low]
    rest = [g for g in order if g not in low]
    step = max(1, len(rest) // max(1, INTERPOLATION_SAMPLE - len(keep)))
    return keep + rest[::step]


# ------------------------------------------------------------------ instances vs statics

def _style(v):
    return v.names.get("17") or v.names.get("2") or ""


KERN_ALPHABET_MAX = 450


def kern_alphabet(view):
    """Printable ASCII plus every character whose glyph takes part in a GPOS pair (either side).

    ASCII alone missed RT's E-12: the hidden pairs after & and @ were & + Cyrillic and Greek.
    Capped at KERN_ALPHABET_MAX characters (a test text of that many squared).
    """
    chars = set(KERN_ALPHABET)
    font = view.font
    if "GPOS" in font:
        glyphs = set()
        for lk in font["GPOS"].table.LookupList.Lookup:
            for st in lk.SubTable:
                st = getattr(st, "ExtSubTable", st)
                if getattr(st, "LookupType", lk.LookupType) != 2 or not hasattr(st, "Coverage"):
                    continue
                glyphs.update(st.Coverage.glyphs)
                if st.Format == 1:
                    for ps in st.PairSet:
                        glyphs.update(r.SecondGlyph for r in ps.PairValueRecord)
                else:
                    glyphs.update(st.ClassDef2.classDefs)
        import unicodedata
        extra = sorted(chr(c) for c, g in view.cmap.items()
                       if g in glyphs and c > 0x7F and unicodedata.category(chr(c))[0] in "LNPS")
        chars.update(extra[:KERN_ALPHABET_MAX - len(chars)])
    return sorted(chars)


def pair_text(*views, limit=6000):
    """Text made of the font's own kerning pairs: every first glyph of a pair lookup followed by one
    representative of each second class it kerns (format 2) or each second glyph (format 1).

    Covering the first glyph is what matters for hidden pairs (RT P-04/E-12), so all first glyphs
    are kept; second classes behave alike, so one member each is enough. A few thousand characters
    instead of the 200 000 of a de Bruijn text over every kerned character.
    """
    out = []
    seen = set()
    for v in views:
        for p in v._memo(("kernpairs", limit), lambda v=v: _kern_pairs(v, limit)):
            if p not in seen:
                seen.add(p)
                out.append(p)
                if len(out) == limit:
                    return "".join(out)
    return "".join(out)


def _kern_pairs(v, limit):
    """The first `limit` distinct pairs of one font, kept on the view: a variable font is paired
    with a static for every instance, and walking its class matrix each time cost a second."""
    if "GPOS" not in v.font:
        return []
    font = v.font
    rev = {}
    for c, g in sorted(v.cmap.items()):
        rev.setdefault(g, chr(c))
    pairs, seen = [], set()

    def add(p):
        if p not in seen:
            seen.add(p)
            pairs.append(p)
        return len(pairs) >= limit

    for lk in font["GPOS"].table.LookupList.Lookup:
        for st in lk.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if getattr(st, "LookupType", lk.LookupType) != 2 or not hasattr(st, "Coverage"):
                continue
            if st.Format == 1:
                for g, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for r in ps.PairValueRecord:
                        if g in rev and r.SecondGlyph in rev and add(rev[g] + rev[r.SecondGlyph]):
                            return pairs
            else:
                reps = {}
                for g2, c2 in sorted(st.ClassDef2.classDefs.items()):
                    if g2 in rev:
                        reps.setdefault(c2, rev[g2])
                for g in st.Coverage.glyphs:
                    if g not in rev:
                        continue
                    row = st.Class1Record[st.ClassDef1.classDefs.get(g, 0)].Class2Record
                    for c2, ch in reps.items():
                        if c2 < len(row) and _nonzero_value(row[c2]) and add(rev[g] + ch):
                            return pairs
    return pairs


def _nonzero_value(rec):
    for val in (getattr(rec, "Value1", None), getattr(rec, "Value2", None)):
        if val is not None and (any(getattr(val, a, 0) for a in ("XPlacement", "YPlacement", "XAdvance", "YAdvance"))
                                or any(getattr(val, a, None) is not None for a in ("XPlaDevice", "XAdvDevice"))):
            return True
    return False


def _kern_text(alphabet=None):
    """Every ordered pair of the alphabet exactly once (a de Bruijn sequence of order 2)."""
    alphabet = alphabet or KERN_ALPHABET
    k = len(alphabet)
    a = [0] * (2 * k)
    seq = []

    def db(t, p):
        if t > 2:
            if 2 % p == 0:
                seq.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    seq.append(seq[0])
    return "".join(alphabet[i] for i in seq)


def _shape(path, text, variations=None):
    import uharfbuzz as hb
    with open(path, "rb") as fh:
        data = fh.read()
    font = hb.Font(hb.Face(hb.Blob(data)))
    if variations:
        font.set_variations(variations)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, LAYOUT_OFF)
    from ..hbshim import rows
    return [(cl, ax, dx, dy) for _, cl, ax, _, dx, dy in rows(buf)]


SAMPLE = 4000  # glyphs compared per instance; CJK fonts are sampled, Latin ones are compared whole
# composite offsets interpolate to fractions and round at export: about 1 unit between an instance
# read in place and a static exported from the same source (seen with ﬁ, Į)
OUTLINE_TOL = 2


def _comparable(vf, st):
    """Glyph pairs to compare: by name when both fonts have real names, else through the cmap.

    Fonts with more than SAMPLE glyphs keep everything below U+3000 (Latin, symbols,
    punctuation) and an even spread of the rest, so a 28 000-glyph CJK instance takes
    seconds, not minutes; the finding says how many glyphs were compared.
    """
    def real(v):  # post 3.0 fonts get generated names (glyph00123) that mean different glyphs per font
        return not any(g.startswith("glyph") and g[5:].isdigit() for g in v.glyph_order)
    if real(vf) and real(st):
        names = set(st.glyph_order)
        pairs = [(g, g) for g in vf.glyph_order if g in names]
    else:
        pairs = [(vf.cmap[c], st.cmap[c]) for c in sorted(set(vf.cmap) & set(st.cmap))]
    if len(pairs) <= SAMPLE:
        return pairs, len(pairs)
    low = {vf.cmap[c] for c in vf.cmap if c < 0x3000}
    keep = [p for p in pairs if p[0] in low]
    rest = [p for p in pairs if p[0] not in low]
    step = max(1, len(rest) // max(1, SAMPLE - len(keep)))
    return keep + rest[::step], len(pairs)


@check(id="vf.vs_static", category="G", scope="package",
       title="Named instances match the static fonts",
       classification="Variable font / Instances vs statics / Widths, outlines, spacing",
       what="each named instance has the same advance widths (hmtx + HVAR) as the static font of the same style "
            "in the same lineage; outline bounds match for the first, middle and last instance (and wherever a "
            "width differs); every ASCII pair and every kerning pair of either font is spaced the same way "
            "(HarfBuzz, kerning on, ligatures off)",
       basis="Users switch between the variable and the static fonts of one family; documents must not reflow "
             "(e.g. pairs kerned in the statics but not in the VF).",
       fix="Export statics and variable font from the same source state; check kerning subtables of the VF.",
       severity="medium",
       symptoms=("All applications: text reflows when switching between the variable font and the statics",))
def vs_static(views, ctx=None):
    by_lineage = defaultdict(list)
    texts = {}
    for v in views:
        if v.ok and v.is_sfnt:
            by_lineage[v.lineage or ""].append(v)
    done = set()
    for lineage, vs in sorted(by_lineage.items(), key=lambda kv: (kv[0] != "Desktop", kv[0])):
        statics = {}
        for s in vs:
            if not s.variable:
                statics.setdefault(_style(s), []).append(s)
        for vf in [x for x in vs if x.variable]:
            # one lineage per variable design is enough: App/Desktop copies share outlines
            if vf.outline_key in done:
                continue
            done.add(vf.outline_key)
            font = vf.font
            for inst in font["fvar"].instances:
                name = _name(font, inst.subfamilyNameID)
                for st in statics.get(name, []):
                    if st.facts["glyphs"]["cmap"] != vf.facts["glyphs"]["cmap"] and \
                            abs(st.facts["glyphs"]["count"] - vf.facts["glyphs"]["count"]) > 0:
                        continue  # a static of another sub-family with the same style name
                    if st.rel not in texts:
                        # ASCII pairs always, plus every kerning pair either font defines
                        texts[st.rel] = _kern_text() + pair_text(st, vf)
                    k = font["fvar"].instances.index(inst)
                    n = len(font["fvar"].instances)
                    full = k in (0, n // 2, n - 1)
                    yield from _compare_instance(vf, st, name, dict(inst.coordinates), texts[st.rel], full_outlines=full)
                    st.release()
            vf.release()


def feature_variation_map(font, coords):
    """Glyph substitutions FeatureVariations (rvrn) make at a location, e.g. bracket layers.

    The instance is read glyph by glyph, which does not run GSUB; without this the
    italic or heavy alternates swapped in by FeatureVariations look like differences.
    """
    from fontTools.varLib.models import normalizeLocation, piecewiseLinearMap
    if "GSUB" not in font or not getattr(font["GSUB"].table, "FeatureVariations", None):
        return {}
    axes = font["fvar"].axes
    loc = normalizeLocation(coords, {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in axes})
    if "avar" in font:
        for tag, seg in font["avar"].segments.items():
            if tag in loc and seg:
                loc[tag] = piecewiseLinearMap(loc[tag], seg)
    table = font["GSUB"].table
    lookups = table.LookupList.Lookup
    mapping = {}
    for rec in table.FeatureVariations.FeatureVariationRecord:
        conds = rec.ConditionSet.ConditionTable if rec.ConditionSet else []
        if all(c.Format == 1 and c.FilterRangeMinValue - 1e-6 <= loc.get(axes[c.AxisIndex].axisTag, 0) <= c.FilterRangeMaxValue + 1e-6
               for c in conds):
            for sub in rec.FeatureTableSubstitution.SubstitutionRecord:
                for li in sub.Feature.LookupListIndex:
                    lk = lookups[li]
                    for st in lk.SubTable:
                        st = getattr(st, "ExtSubTable", st)
                        for g, o in getattr(st, "mapping", {}).items():
                            mapping.setdefault(g, o)
            break  # the first matching record applies
    return mapping


def _hvar_widths(font, coords):
    """Advance widths at a location from hmtx + HVAR: additions, no outline is computed."""
    from fontTools.varLib.models import normalizeLocation, piecewiseLinearMap
    from fontTools.varLib.varStore import VarStoreInstancer
    if "HVAR" not in font:
        return None
    axes = font["fvar"].axes
    loc = normalizeLocation(coords, {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in axes})
    if "avar" in font:
        for tag, seg in font["avar"].segments.items():
            if tag in loc and seg:
                loc[tag] = piecewiseLinearMap(loc[tag], seg)
    hvar = font["HVAR"].table
    inst = VarStoreInstancer(hvar.VarStore, axes, loc)
    mapping = hvar.AdvWidthMap.mapping if hvar.AdvWidthMap else None
    order = font.getGlyphOrder()
    hmtx = font["hmtx"].metrics
    out = {}
    for gid, g in enumerate(order):
        idx = mapping[g] if mapping is not None else gid  # implicit mapping: outer 0, inner = glyph id
        out[g] = hmtx[g][0] + inst[idx]
    return out


def _compare_instance(vf, st, name, coords, text, full_outlines=True):
    gs = vf.font.getGlyphSet(location=coords)
    sgs = st.glyph_set
    hv = _hvar_widths(vf.font, coords)
    swap = feature_variation_map(vf.font, coords)
    # statics exported from Glyphs move a bracket alternate under the base glyph's name and keep the
    # alternate's name for the old design, so swap targets have no same-named twin in the static
    targets = set(swap.values())
    widths, bounds = [], []
    pairs, total = _comparable(vf, st)
    for gv, gst in pairs:
        if gv in targets:
            continue
        gv = swap.get(gv, gv)
        try:
            w1 = hv[gv] if hv is not None else gs[gv].width
            w2 = st.widths[gst]
        except KeyError:
            continue
        differs = abs(w1 - w2) > 0.5
        if differs:
            widths.append(f"{glyph_label(st, gst)}: VF {round(w1, 1):g}, static {w2}")
        if not (full_outlines or differs):
            continue
        p1, p2 = BoundsPen(gs), BoundsPen(sgs)
        gs[gv].draw(p1)
        sgs[gst].draw(p2)
        b1, b2 = p1.bounds, p2.bounds
        if (b1 is None) != (b2 is None) or (b1 and max(abs(x - y) for x, y in zip(b1, b2)) > OUTLINE_TOL):
            bounds.append(glyph_label(st, gst))
    label = f"{name} @ {', '.join(f'{k} {val:g}' for k, val in coords.items())}"
    if not full_outlines:
        label += " (outlines checked where widths differ)"
    if len(pairs) < total:
        label += f" ({len(pairs)} of {total} glyphs compared)"
    files = [vf.rel, st.rel]
    if widths:
        yield Hit(key=f"instance widths differ from static", files=files, measured=f"{label}: {len(widths)} glyphs",
                  expected="same advance widths", glyphs=widths,
                  summary=f"{len(widths)} advance widths of the instance differ from the static font")
    if bounds:
        yield Hit(key=f"instance outlines differ from static", files=files, measured=f"{label}: {len(bounds)} glyphs",
                  expected=f"same outlines (bounds within {OUTLINE_TOL} units)", glyphs=bounds, action="confirm",
                  summary=f"{len(bounds)} glyph outlines of the instance differ from the static font")
    a = _shape(vf.path, text, coords)
    b = _shape(st.path, text)
    if len(a) != len(b):
        yield Hit(key="instance shapes differently from static", files=files, measured=f"{label}: {len(a)} vs {len(b)} glyphs",
                  expected="same glyph sequence", summary="the instance and the static font shape the test text differently")
        return
    # HarfBuzz adds the kerning of a pair to the advance of its first glyph; with equal widths
    # (checked above) any difference in that advance is a difference in kerning
    kerned = []
    if not widths:
        for k in range(1, len(a)):
            if abs(a[k - 1][1] - b[k - 1][1]) > 1:
                left, right = text[a[k - 1][0]], text[a[k][0]]
                item = f"{left}{right}: VF {a[k - 1][1]}, static {b[k - 1][1]}"
                if item not in kerned:  # the pair text may hold a pair twice
                    kerned.append(item)
    if kerned:
        yield Hit(key="instance kerning differs from static", files=files, measured=f"{label}: {len(kerned)} pairs",
                  expected="same spacing of every character pair", glyphs=kerned,
                  summary=f"{len(kerned)} character pairs are spaced differently in the instance than in the static font")
