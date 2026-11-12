"""Font menus as operating systems and apps would build them, computed from the tables.

RT installed the fonts on Windows 11 and macOS and photographed the menus
(E-01 … E-25). Most of what they saw follows from a handful of rules, so the
menus can be predicted before anything is installed:

  Windows GDI (Word, Notepad, PowerPoint): family = name ID 1, cut to 31
      characters (LOGFONT.lfFaceName is 32 with the null); style = ID 2 (RIBBI).
      Names that become equal after the cut merge into one menu item.
  Windows WWS (Notepad's font dialog, Settings): family = ID 21, else ID 16 plus
      every word of ID 17 that DirectWrite does not read as weight, width or
      slope; a usWidthClass other than 5 is shown as a width word.
  macOS (Font Book, TextEdit, Illustrator) in a given language: the name records
      of that language win; a language with IDs 1/2 but no 16/17 makes every
      style of the family look like Regular or Bold.
  Variable fonts on macOS: the default instance is listed under the style name
      (ID 17, else ID 2), the others under their instance names.

The simulation is a prediction; the checklist page lets a person confirm each
symptom on a real system, as RT did with screenshots.
"""

import re
from collections import defaultdict

# DirectWrite's weight / width / slope vocabulary (lower case, no spaces)
DW_WEIGHT = {"thin", "hairline", "extralight", "ultralight", "light", "semilight", "demilight", "regular", "normal",
             "book", "medium", "semibold", "demibold", "bold", "extrabold", "ultrabold", "black", "heavy",
             "extrablack", "ultrablack"}
DW_WIDTH = {"ultracondensed", "extracondensed", "condensed", "semicondensed", "semiexpanded", "expanded",
            "extraexpanded", "ultraexpanded", "narrow", "wide", "compressed", "extended"}
DW_SLOPE = {"italic", "oblique"}
WIDTH_NAMES = {1: "Ultra-condensed", 2: "Extra-condensed", 3: "Condensed", 4: "Semi-condensed", 5: "",
               6: "Semi-expanded", 7: "Expanded", 8: "Extra-expanded", 9: "Ultra-expanded"}
LANGS = {"0x409": "English", "0x804": "Simplified Chinese", "0x404": "Traditional Chinese", "0x411": "Japanese",
         "0x412": "Korean", "0x419": "Russian", "0x407": "German", "0x40C": "French"}
GDI_LIMIT = 31


def _words(s):
    return [w for w in re.split(r"\s+", s or "") if w]


def _installed_groups(views):
    """Fonts a user installs together: one lineage, one container (Desktop TTF, App TTF, OTF …)."""
    groups = defaultdict(list)
    for v in views:
        if v.ok and v.lineage != "Web" and v.fmt in ("OTF", "TTF"):
            groups[(v.lineage or "", v.fmt)].append(v)
    return [(f"{lin + ' ' if lin else ''}{fmt}", vs) for (lin, fmt), vs in sorted(groups.items())]


def _localized(v, lang):
    """Name strings of one Windows language (0x804 …), read from the font."""
    if lang == "0x409":
        return dict(v.names)
    out = {}
    for rec in v.font["name"].names:
        if rec.platformID == 3 and f"0x{rec.langID:X}" == lang:
            try:
                out[str(rec.nameID)] = rec.toUnicode()
            except Exception:
                pass
    return out


# ------------------------------------------------------------------ simulations

def windows_gdi(vs):
    menu = defaultdict(list)
    for v in vs:
        fam = v.names.get("1") or ""
        menu[fam[:GDI_LIMIT]].append((v.names.get("2") or "", v.rel, len(fam)))
    items = []
    for name, styles in sorted(menu.items()):
        stnames = [st for st, _, _ in styles]
        collapsed = len(stnames) - len(set(stnames))
        truncated = any(n >= GDI_LIMIT for _, _, n in styles)
        items.append({"family": name, "styles": sorted(set(stnames)), "files": [rel for _, rel, _ in styles],
                      "truncated": truncated, "lost": collapsed})
    return items


def windows_wws(vs):
    rows = defaultdict(list)
    for v in vs:
        if v.variable:
            continue
        if v.names.get("21"):
            fam, style = v.names["21"], v.names.get("22") or v.names.get("2") or ""
        else:
            base = v.names.get("16") or v.names.get("1") or ""
            style_words = _words(v.names.get("17") or v.names.get("2"))
            extra = [w for w in style_words if w.lower() not in DW_WEIGHT | DW_WIDTH | DW_SLOPE]
            fam = " ".join([base] + extra)
            style = " ".join(w for w in style_words if w not in extra) or "Regular"
        width = WIDTH_NAMES.get(v.style.get("width_class") or 5, "")
        rows[fam].append((f"{width} {style}".strip(), v.rel))
    return [{"family": f, "styles": [s for s, _ in sorted(st)], "files": [r for _, r in st],
             "width_words": sorted({s.split()[0] for s, _ in st if s.split() and s.split()[0] in WIDTH_NAMES.values() and s.split()[0]})}
            for f, st in sorted(rows.items())]


def macos(vs, lang):
    fams = defaultdict(list)
    for v in vs:
        if v.variable:
            continue
        names = _localized(v, lang)
        if not names:
            names = dict(v.names)  # no record in this language: English is shown
        fam = names.get("16") or names.get("1") or v.names.get("16") or v.names.get("1")
        style = names.get("17") or names.get("2") or v.names.get("17") or v.names.get("2")
        fams[fam].append((style, v.rel))
    out = []
    for fam, sts in sorted(fams.items()):
        names = [s for s, _ in sts]
        out.append({"family": fam, "styles": sorted(set(names)), "files": [r for _, r in sts],
                    "lost": len(names) - len(set(names))})
    return out


def fontbook(vs, lang):
    """Font Book / TextEdit: families grouped by the English typographic family, shown with the
    localized names; styles read from the localized ID 17, else ID 2 — duplicates cannot be told apart."""
    fams = defaultdict(list)
    for v in vs:
        if v.variable:
            continue
        fams[v.names.get("16") or v.names.get("1")].append(v)
    out = []
    for key, members in sorted(fams.items()):
        loc = [_localized(v, lang) or dict(v.names) for v in members]
        shown = loc[0].get("16") or loc[0].get("1") or key
        styles = [n.get("17") or n.get("2") or "" for n in loc]
        out.append({"family": shown, "english": key, "styles": sorted(set(styles)), "files": [v.rel for v in members],
                    "lost": len(styles) - len(set(styles))})
    return out


def macos_variable(v):
    font = v.font
    default = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
    style = v.names.get("17") or v.names.get("2")
    shown = []
    for inst in font["fvar"].instances:
        at_default = all(abs(inst.coordinates.get(t, d) - d) < 1e-6 for t, d in default.items())
        name = style if at_default else font["name"].getDebugName(inst.subfamilyNameID)
        shown.append(name)
    real = [font["name"].getDebugName(i.subfamilyNameID) for i in font["fvar"].instances]
    return {"family": v.names.get("16") or v.names.get("1"), "shown": shown,
            "duplicates": sorted({n for n in shown if shown.count(n) > 1}),
            "missing": sorted(set(real) - set(shown)), "file": v.rel}


def simulate(views):
    """Every menu for every group of fonts installed together."""
    out = []
    for label, vs in _installed_groups(views):
        langs = sorted({f"0x{r.langID:X}" for v in vs for r in v.font["name"].names if r.platformID == 3})
        group = {"group": label, "gdi": windows_gdi(vs), "wws": windows_wws(vs),
                 "macos": {lang: macos(vs, lang) for lang in langs},
                 "fontbook": {lang: fontbook(vs, lang) for lang in langs},
                 "macos_vf": [macos_variable(v) for v in vs if v.variable]}
        for v in vs:
            v.release()
        out.append(group)
    return out


# ------------------------------------------------------------------ symptoms

def symptoms(sim, issues):
    """Concrete predicted symptoms with the parent issue (by check id) when the report has one."""
    parent = {}
    for i in issues:
        parent.setdefault(i["check"], i["id"])
    out = []

    def add(env, text, check, files):
        out.append({"environment": env, "symptom": text, "parent": parent.get(check, "—"), "check": check,
                    "files": files[:50], "status": "predicted", "screenshot": ""})

    for g in sim:
        lab = g["group"]
        cut = [it for it in g["gdi"] if it["truncated"]]
        for it in cut:
            add(f"Windows 11, Word ({lab})", f"text set in “{it['family']}” (31-character GDI name) may fall back to a "
                f"system font for characters outside Latin; the document stores the fallback name", "names.gdi_length", it["files"])
            add(f"Windows 11, PowerPoint ({lab})", f"the font list gets an extra item “{it['family'][:30]}” (30 characters); "
                f"choosing it renders in a fallback font", "names.gdi_length", it["files"])
        for it in g["gdi"]:
            if it["lost"]:
                add(f"Windows 11, Notepad / Word ({lab})", f"{it['lost'] + len(it['styles'])} fonts collapse into the menu item "
                    f"“{it['family']}” with only {', '.join(it['styles'])}; {it['lost']} cannot be selected",
                    "names.gdi_length" if it["truncated"] else "names.unique", it["files"])
        if cut:
            add(f"macOS, Word / PowerPoint for Mac ({lab})", "documents saved with a 31-character family name open in Word "
                "for Windows with the fallback behaviour above", "names.gdi_length", [f for it in cut for f in it["files"]])
        rows = g["wws"]
        if len(rows) > 1 and any(set(_words(r["family"])) - set(_words(rows[0]["family"])) for r in rows[1:]):
            add(f"Windows 11, Notepad font dialog ({lab})", f"the family is split into {len(rows)} rows: "
                + "; ".join(f"“{r['family']}” ({', '.join(r['styles'][:6])})" for r in rows[:8]), "names.wws",
                [f for r in rows for f in r["files"]])
        widths = sorted({w for r in rows for w in r["width_words"]})
        if widths:
            add(f"Windows 11, Notepad font dialog ({lab})", f"styles carry width words: {', '.join(widths)}",
                "os2.width_class", [f for r in rows if r["width_words"] for f in r["files"]])
        for lang, fams in g["macos"].items():
            if lang == "0x409":
                continue
            for f in g["fontbook"].get(lang, []):
                if f["lost"]:
                    add(f"macOS in {LANGS.get(lang, lang)}, Font Book / TextEdit ({lab})",
                        f"{len(f['files'])} fonts of “{f['english']}” appear as family “{f['family']}” with only "
                        f"{', '.join(f['styles'])}; TextEdit offers {len(f['styles'])} of {len(f['files'])}",
                        "names.localized", f["files"])
            if len(fams) > len(g["macos"].get("0x409", fams)):
                add(f"macOS in {LANGS.get(lang, lang)}, Illustrator ({lab})", f"the font menu lists {len(fams)} families "
                    f"instead of {len(g['macos'].get('0x409', []))}; style names read as ID 1 + ID 2",
                    "names.localized", [x for f in fams for x in f["files"]])
        for vf in g["macos_vf"]:
            if vf["duplicates"] or vf["missing"]:
                add(f"macOS, Font Book / TextEdit ({lab})", f"variable font “{vf['family']}”: "
                    + (f"“{', '.join(vf['duplicates'])}” listed twice" if vf["duplicates"] else "")
                    + ("; " if vf["duplicates"] and vf["missing"] else "")
                    + (f"“{', '.join(vf['missing'])}” missing" if vf["missing"] else ""), "vf.default_instance", [vf["file"]])
    for k, s in enumerate(out, 1):
        s["id"] = f"S-{k:02d}"
    return out
