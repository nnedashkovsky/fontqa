"""Release readiness for the studio's own fonts (category R, profile "release").

What stores reject or customers stumble over:
names that do not match between family, styles and files; missing formats;
missing copyright or license information; a promo font.json whose numbers no
longer describe the font (P-001: banner facts come only from font.json).
"""

import os
import re
from collections import defaultdict

from . import Hit, check, families, files_of, installable


@check(id="release.formats", category="R", scope="package",
       title="Formats for desktop and web",
       classification="Release / Formats / Desktop and web",
       what="each family ships an OTF or TTF and a WOFF2",
       basis="Stores take OTF or TTF (Fontspring, Creative Fabrica, MyFonts); web licenses need WOFF2.",
       fix="Export the missing formats.", severity="low", action="confirm")
def formats(views, ctx=None):
    fams = defaultdict(set)
    for v in views:
        if v.ok and not v.variable and v.lineage != "Web":
            fams[v.names.get("16") or v.family].add(v.fmt)
    web = [v for v in views if v.ok and v.fmt == "WOFF2"]
    # web fonts with obfuscated names cannot be matched to a family; count them for all
    anonymous_woff2 = any(len(v.family) <= 1 or not v.family.isprintable() for v in web)
    named_woff2 = {v.names.get("16") or v.family for v in web}
    for fam, fmts in sorted(fams.items()):
        missing = []
        if not fmts & {"OTF", "TTF"}:
            missing.append("OTF or TTF")
        if not (anonymous_woff2 or fam in named_woff2):
            missing.append("WOFF2")
        if missing:
            files = [v.rel for v in views if v.ok and v.lineage != "Web" and (v.names.get("16") or v.family) == fam]
            yield Hit(key=f"missing {' and '.join(missing)}", files=files,
                      measured=", ".join(sorted(fmts)), expected="OTF/TTF and WOFF2",
                      summary=f"{fam}: no {' and no '.join(missing)}")


@check(id="release.file_names", category="R", scope="file", applies=installable,
       title="File name matches the PostScript name",
       classification="Release / Names / File names",
       what="the file name (without extension) equals name ID 6",
       basis="Stores check that family, styles and files name the same thing; FamilyName-Style is the "
             "convention customers recognise.",
       fix="Name files after the PostScript name (Glyphs does this by default).", severity="low", action="confirm")
def file_names(v):
    stem = os.path.splitext(os.path.basename(v.rel))[0]
    ps = v.names.get("6") or ""
    if stem != ps:
        yield Hit(key="file name ≠ PostScript name", measured=f"{stem} / {ps}", expected=ps,
                  summary=f"file {stem} vs PostScript name {ps}")


@check(id="release.passport", category="R", scope="family",
       title="Copyright, license and credits are filled",
       classification="Release / Font info / Copyright and license",
       what="name IDs 0 (copyright), 8 (manufacturer), 9 (designer), 11/12 (URLs), 13/14 (license) are present",
       basis="Customers and stores read these fields; a font without copyright and license text is "
             "rejected by some stores and is hard to defend.",
       fix="Fill Font Info → General / Other in the source.", severity="low", action="confirm")
def passport(group):
    copyright_missing = [v for v in group if installable(v) and not v.names.get("0")]
    if copyright_missing:
        yield Hit(key="ID 0 (copyright) empty", files=files_of(copyright_missing), measured="empty",
                  expected="copyright notice", summary="name ID 0 (copyright) is empty", action="fix", severity="medium")
    labels = {"8": "manufacturer", "9": "designer", "11": "vendor URL", "12": "designer URL",
              "13": "license", "14": "license URL"}
    by_missing = {}
    for v in group:
        if installable(v):
            missing = tuple(nid for nid in labels if not v.names.get(nid))
            if missing:
                by_missing.setdefault(missing, []).append(v)
    for missing, vs in by_missing.items():
        shown = ", ".join(f"{nid} {labels[nid]}" for nid in missing)
        yield Hit(key="font info fields empty", files=files_of(vs), measured=f"empty: {shown}",
                  expected="all filled", summary=f"empty name IDs: {shown}")


@check(id="release.version", category="R", scope="family",
       title="Release version",
       classification="Release / Version / Version number",
       what="the version is 1.000 or higher", basis="Versions below 1.0 read as beta to customers.",
       fix="Set the release version in the source.", severity="low", action="confirm")
def version(group):
    low = [v for v in group if (v.style.get("revision") or 0) < 1]
    if low:
        yield Hit(key="version below 1.0", files=files_of(low), measured=str(low[0].style.get("revision")),
                  expected="≥ 1.000", summary=f"version {low[0].style.get('revision')} is below 1.0")


@check(id="release.font_json", category="R", scope="package",
       title="Promo facts (font.json) describe this build",
       classification="Release / Promo / font.json facts",
       what="glyph and character counts, features and PostScript names in design/font.json match the fonts",
       basis="P-001: every number on banners and in store texts comes from font.json; it must describe "
             "the build that is sold.",
       fix="Re-run tools/promo/font_facts.py on the new build.", severity="medium", requires=("font_json",))
def font_json(views, ctx=None):
    data = (ctx or {}).get("font_json")
    if not data:
        return
    by_ps = {v.names.get("6"): v for v in views if v.ok and installable(v)}
    for st in (data.get("facts") or {}).get("styles", []):
        v = by_ps.get(st.get("postscript"))
        if v is None:
            yield Hit(key="style in font.json not in the build", measured=st.get("postscript"),
                      expected="a font with this PostScript name", summary=f"font.json lists {st.get('postscript')}, the build does not")
            continue
        diffs = []
        if st.get("glyphs") != v.facts["glyphs"]["count"]:
            diffs.append(f"glyphs {st.get('glyphs')} → {v.facts['glyphs']['count']}")
        if st.get("unicodes") != v.facts["glyphs"]["cmap"]:
            diffs.append(f"characters {st.get('unicodes')} → {v.facts['glyphs']['cmap']}")
        feats = sorted(((v.facts.get("layout") or {}).get("GSUB") or {}).get("features", []))
        if st.get("features") is not None and sorted(st["features"]) != feats:
            diffs.append("features " + ", ".join(sorted(set(st["features"]) ^ set(feats))))
        if diffs:
            yield Hit(key="font.json is out of date", files=[v.rel], measured="; ".join(diffs),
                      expected="font.json = build", summary=f"{st.get('postscript')}: " + "; ".join(diffs))
