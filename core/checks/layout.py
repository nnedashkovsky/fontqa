"""OpenType layout (category D).

The checks read GSUB/GPOS structurally rather than shaping text: which scripts
are registered, which glyphs no feature can reach, which kerning pairs are
hidden behind an earlier subtable. The last one is RT's P-04: a class-based
PairPos subtable (format 2) "matches" every first glyph in its coverage, even
with a zero value, so a later subtable never sees those first glyphs. HarfBuzz
and DirectWrite behave the same way.
"""

from collections import defaultdict

from . import Hit, check, sfnt
from ..fontview import glyph_label

SCRIPT_TAGS = {"Latn": "latn", "Cyrl": "cyrl", "Grek": "grek", "Arab": "arab", "Hebr": "hebr",
               "Armn": "armn", "Geor": "geor", "Thai": "thai", "Hani": "hani", "Kana": "kana",
               "Hira": "kana", "Hang": "hang", "Deva": "dev2", "Beng": "bng2"}
SUFFIX_FEATURES = [(".sc", "smcp/c2sc"), (".smcp", "smcp"), (".c2sc", "c2sc"), (".case", "case"),
                   (".tf", "tnum"), (".tnum", "tnum"), (".osf", "onum"), (".onum", "onum"), (".lf", "lnum"),
                   (".sups", "sups"), (".sinf", "sinf"), (".subs", "subs"), (".numr", "numr/frac"),
                   (".dnom", "dnom/frac"), (".ss", "ssXX"), (".cv", "cvXX"), (".salt", "salt"),
                   (".alt", "salt/aalt"), (".swsh", "swsh"), (".locl", "locl"), (".liga", "liga"),
                   (".dlig", "dlig"), (".init", "init"), (".fina", "fina"), (".medi", "medi")]
NOT_IN_AALT = {"aalt", "locl", "ccmp", "rvrn", "init", "medi", "fina", "isol", "rlig", "calt", "clig",
               "liga", "dlig", "frac", "numr", "dnom", "rclt", "ljmo", "vjmo", "tjmo"}
IGNORED_GLYPHS = {".notdef", ".null", "NULL", "nonmarkingreturn", "CR", "uni000D", "uni0000"}


def _lookups(table):
    """Lookups with Extension (GSUB 7 / GPOS 9) unwrapped: list of (type, [subtables])."""
    out = []
    if not table.LookupList:
        return out
    for lk in table.LookupList.Lookup:
        subs, ltype = [], lk.LookupType
        for st in lk.SubTable:
            if ltype in (7, 9) and hasattr(st, "ExtSubTable"):
                subs.append(st.ExtSubTable)
                ltype_real = st.ExtensionLookupType
            else:
                subs.append(st)
                ltype_real = ltype
        out.append((ltype_real if subs else ltype, subs))
    return out


def _feature_lookups(table, tag=None, exclude=()):
    idx = set()
    if table.FeatureList:
        for fr in table.FeatureList.FeatureRecord:
            if (tag is None or fr.FeatureTag == tag) and fr.FeatureTag not in exclude:
                idx.update(fr.Feature.LookupListIndex)
    return idx


def feature_single_map(font, tag):
    """glyph -> first output of single/alternate substitutions in feature `tag`."""
    out = {}
    if "GSUB" not in font:
        return out
    table = font["GSUB"].table
    lookups = _lookups(table)
    for i in sorted(_feature_lookups(table, tag)):
        ltype, subs = lookups[i]
        for st in subs:
            if ltype == 1:
                for g, o in st.mapping.items():
                    out.setdefault(g, o)
            elif ltype == 3:
                for g, alts in st.alternates.items():
                    if alts:
                        out.setdefault(g, alts[0])
    return out


@check(id="layout.scripts", category="D", scope="file", applies=sfnt,
       title="Scripts of the character set are registered",
       classification="OpenType layout / Script list / Missing scripts",
       what="every script with at least 10 letters in the cmap has a script record in GSUB and GPOS",
       basis="Shaping engines pick features by script; a script only reachable through DFLT loses "
             "language-specific behaviour (e.g. for 'hani').",
       fix="Let the export register the scripts (features with script-specific lookups, or explicit script statements).",
       severity="medium", action="confirm")
def scripts(v):
    have = {}
    for tag in ("GSUB", "GPOS"):
        lay = (v.facts.get("layout") or {}).get(tag)
        if lay:
            have[tag] = set(lay["scripts"])
    counts = v.facts["glyphs"]["scripts"]
    for code, n in sorted(counts.items()):
        ot = SCRIPT_TAGS.get(code)
        if not ot or n < 10:
            continue
        missing = [t for t, s in have.items() if ot not in s]
        if missing:
            yield Hit(key=f"script '{ot}' not registered", measured=f"{n} {code} characters; not in {', '.join(missing)}",
                      expected=f"'{ot}' in {', '.join(missing)}", summary=f"'{ot}' is not registered in {', '.join(missing)}")


@check(id="layout.unreachable", category="D", scope="outline", applies=sfnt,
       title="Every glyph is reachable",
       classification="OpenType layout / Glyph access / Unreachable glyphs",
       what="every glyph can be reached from the cmap through some feature (including aalt) or as a component",
       basis="A glyph no feature produces cannot be typed; usually a missing feature for a suffix (.ss01, .sc, .tf).",
       fix="Add the glyph to its feature (the suffix suggests which) or remove it from the export.",
       severity="medium", symptoms=("All applications: alternates drawn for the font cannot be used",))
def unreachable(v):
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = True
    s = subset.Subsetter(opts)
    s.populate(unicodes=list(v.cmap))
    font = v.font
    s._closure_glyphs(font)
    reached = set(s.glyphs_retained)
    left = [g for g in v.glyph_order if g not in reached and g not in IGNORED_GLYPHS]
    if left:
        hints = defaultdict(list)
        for g in left:
            feat = next((f for suf, f in SUFFIX_FEATURES if suf in g), None)
            hints[feat].append(g)
        shown = [f"{g} → {feat}?" if feat else g for feat, gs in hints.items() for g in gs]
        yield Hit(key="glyphs no feature reaches", measured=f"{len(left)} glyphs", expected="0",
                  glyphs=shown, summary=f"{len(left)} glyphs cannot be reached from any character")


@check(id="layout.kern_shadowed", category="D", scope="file", applies=sfnt,
       title="No kerning pairs hidden behind earlier subtables",
       classification="OpenType layout / GPOS kern / Unreachable pairs",
       what="no pair in a PairPos subtable has a first glyph that an earlier class-based subtable of the "
            "same lookup already covers",
       basis="A format-2 PairPos subtable applies to every first glyph in its coverage (with value 0 if "
             "the class pair is empty), so later subtables never see it.",
       fix="Move the hidden pairs into the first subtable that covers their first glyph, or split coverage "
           "so it does not overlap.", severity="medium",
       symptoms=("All applications: these pairs are not kerned; a variable font spaces differently from its statics",))
def kern_shadowed(v):
    if "GPOS" not in v.font:
        return
    order = v.font.getGlyphOrder()
    hidden, firsts = 0, set()
    for ltype, subs in _lookups(v.font["GPOS"].table):
        if ltype != 2:
            continue
        covered = set()
        for st in subs:
            cov = st.Coverage.glyphs
            if st.Format == 1:
                for g, ps in zip(cov, st.PairSet):
                    if g in covered:
                        n = sum(1 for r in ps.PairValueRecord if _nonzero(r.Value1) or _nonzero(getattr(r, "Value2", None)))
                        if n:
                            hidden += n
                            firsts.add(g)
            elif st.Format == 2:
                shadow = [g for g in cov if g in covered]
                if shadow:
                    cd1, cd2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                    class2_size = defaultdict(int)
                    for g in order:
                        class2_size[cd2.get(g, 0)] += 1
                    for g in shadow:
                        row = st.Class1Record[cd1.get(g, 0)]
                        n = sum(class2_size[c2] for c2, rec in enumerate(row.Class2Record)
                                if _nonzero(rec.Value1) or _nonzero(getattr(rec, "Value2", None)))
                        if n:
                            hidden += n
                            firsts.add(g)
                # only class-based subtables shadow: format 1 falls through when the pair is absent
                covered.update(cov)
    if hidden:
        yield Hit(key="kerning pairs hidden by earlier subtables", measured=f"{hidden} pairs after {len(firsts)} first glyphs",
                  expected="0", glyphs=[glyph_label(v, g) for g in sorted(firsts)],
                  summary=f"{hidden} kerning pairs never apply (first glyphs covered by an earlier subtable)")


def _nonzero(value):
    if value is None:
        return False
    return any(getattr(value, a, 0) for a in ("XPlacement", "YPlacement", "XAdvance", "YAdvance")) or \
        any(getattr(value, a, None) is not None for a in ("XPlaDevice", "YPlaDevice", "XAdvDevice", "YAdvDevice"))


@check(id="layout.legacy_kern", category="D", scope="file", applies=lambda v: sfnt(v) and v.lineage != "Web",
       title="Legacy kern table for Word",
       classification="OpenType layout / Kerning / Legacy kern table",
       what="an installable font with GPOS kerning also carries a legacy 'kern' table",
       basis="Microsoft Word kerns only from the "
             "legacy 'kern' table; with GPOS alone the text in Word is not kerned. 'kern' holds no class kerning, "
             "so it is a flattened copy of the GPOS pairs.",
       fix="Export a legacy kern table as well (flattened pairs), at least for the Desktop build.",
       severity="low", action="confirm",
       symptoms=("Word: text set in the font is not kerned",))
def legacy_kern(v):
    pairs = (v.facts.get("layout") or {}).get("kern_pairs")
    gpos = (v.facts.get("layout") or {}).get("GPOS") or {}
    if pairs is None and "kern" in gpos.get("features", []):
        yield Hit(key="no legacy kern table", measured="GPOS kerning only", expected="also a 'kern' table",
                  summary="GPOS kerning but no legacy 'kern' table (Word will not kern)")


@check(id="layout.aalt", category="D", scope="file", applies=sfnt,
       title="aalt offers every alternate",
       classification="OpenType layout / GSUB aalt / Missing alternates",
       what="every single or alternate substitution of other features (input → output) is also offered by aalt",
       basis="InDesign's glyph panel offers alternates from aalt only.",
       fix="Let the export rebuild aalt from all features with alternates.", severity="low", action="confirm",
       symptoms=("InDesign: the glyph panel does not offer these alternates",))
def aalt(v):
    if "GSUB" not in v.font:
        return
    table = v.font["GSUB"].table
    if not _feature_lookups(table, "aalt"):
        return
    lookups = _lookups(table)

    def pairs(indices):
        out = set()
        for i in indices:
            ltype, subs = lookups[i]
            for st in subs:
                if ltype == 1:
                    out.update(st.mapping.items())
                elif ltype == 3:
                    out.update((g, a) for g, alts in st.alternates.items() for a in alts)
        return out

    in_aalt = pairs(_feature_lookups(table, "aalt"))
    others = pairs(_feature_lookups(table, exclude=NOT_IN_AALT))
    missing = sorted(others - in_aalt)
    if missing:
        yield Hit(key="substitutions missing from aalt", measured=f"{len(missing)} pairs", expected="0",
                  glyphs=[f"{glyph_label(v, a)} → {glyph_label(v, b)}" for a, b in missing],
                  summary=f"{len(missing)} substitutions of other features are not offered by aalt")


@check(id="layout.marks", category="D", scope="file", applies=sfnt,
       title="Combining marks are positioned",
       classification="OpenType layout / GPOS mark / Mark attachment",
       what="a font with combining marks in its cmap has a GPOS 'mark' feature",
       basis="Without 'mark', base + combining mark sequences stack the mark at its default position.",
       fix="Add anchors (top, bottom…) to bases and marks so the export builds mark/mkmk.", severity="medium",
       symptoms=("All applications: decomposed accents sit in the wrong place, e.g. in Vietnamese or NFD-normalized text",))
def marks(v):
    import unicodedata
    combining = [cp for cp in v.cmap if 0x300 <= cp <= 0x36F and unicodedata.category(chr(cp)) == "Mn"]
    feats = ((v.facts.get("layout") or {}).get("GPOS") or {}).get("features", [])
    if combining and "mark" not in feats:
        yield Hit(key="no mark feature", measured=f"{len(combining)} combining marks, no 'mark'", expected="'mark' feature",
                  summary=f"{len(combining)} combining marks but no GPOS 'mark' feature")
