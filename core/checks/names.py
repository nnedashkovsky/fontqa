"""Names and family structure (categories A and F).

Most high-severity problems in a typical QA report come from here: a family name
that reaches Windows' 31-character GDI limit, localized records that macOS
prefers but which lacked IDs 16/17. These checks only read the name table, so
they run on every installable file (web fonts are named by CSS, and their names
are often obfuscated on purpose).
"""

import re
from collections import defaultdict

from . import Hit, check, families, files_of, installable

RIBBI = {"Regular", "Italic", "Bold", "Bold Italic"}
WEIGHT_WORDS = {
    "thin": 100, "hairline": 100, "extralight": 200, "ultralight": 200, "xlight": 200,
    "light": 300, "lt": 300, "book": 400, "regular": 400, "normal": 400, "rg": 400,
    "medium": 500, "md": 500, "semibold": 600, "demibold": 600, "sbd": 600, "smbd": 600,
    "bold": 700, "bd": 700, "extrabold": 800, "ultrabold": 800, "xbold": 800, "xbd": 800,
    "black": 900, "heavy": 900, "extrablack": 950, "ultrablack": 950,
}
WIDTH_WORDS = {
    "ultracondensed": 1, "extracondensed": 2, "condensed": 3, "semicondensed": 4,
    "narrow": 3, "compressed": 2, "semiexpanded": 6, "expanded": 7, "extended": 7,
    "wide": 7, "extraexpanded": 8, "ultraexpanded": 9,
}
SLOPE_WORDS = {"italic", "oblique", "slanted", "upright", "roman"}


def style_words(style):
    """'Dark Display XBold Italic' -> ['dark', 'display', 'xbold', 'italic']."""
    return [w.lower() for w in re.split(r"[\s\-_]+", style or "") if w]


def non_wws_words(style):
    return [w for w in style_words(style)
            if w not in WEIGHT_WORDS and w not in WIDTH_WORDS and w not in SLOPE_WORDS]


def _quote(s):
    return f"“{s}”"


# ------------------------------------------------------------------ A

@check(id="names.gdi_length", category="A", scope="file", applies=installable,
       title="Family name reaches the Windows GDI limit",
       classification="Names / Windows family / GDI name length",
       what="name ID 1 (and, for variable fonts, family + instance name) is 30 characters or fewer",
       basis="Windows GDI LOGFONT.lfFaceName holds 32 characters including the terminating null; "
             "longer family names are cut at 31.",
       fix="Shorten the family name: abbreviate style words in name ID 1 (e.g. Dark Display XBold → Dk Dis XBd); "
           "IDs 16/17 can keep the full names.",
       severity="high", symptoms=(
           "Word for Windows: text in the font falls back to a system font for some characters",
           "Windows font menus: several styles collapse into one truncated item and cannot be selected"))
def gdi_length(v):
    fam = v.names.get("1") or ""
    if len(fam) >= 31:
        yield Hit(key="name ID 1 is 31+ characters", measured=f"{len(fam)}: {_quote(fam)}",
                  expected="≤ 30 characters", summary=f"name ID 1 has {len(fam)} characters")
    var = v.facts.get("variation")
    if var:
        typo = v.names.get("16") or fam
        long = []
        for inst in var["instances"]:
            words = [w for w in (inst["name"] or "").split() if w not in ("Regular", "Bold", "Italic")]
            name = " ".join([typo] + words)
            if len(name) >= 31:
                long.append(f"{len(name)}: {_quote(name)}")
        if long:
            yield Hit(key="variable instance names are 31+ characters", measured="; ".join(long[:12]),
                      expected="≤ 30 characters for family + instance",
                      summary=f"{len(long)} named instances give Windows family names of 31+ characters")


@check(id="names.ribbi", category="A", scope="file", applies=installable,
       title="Style linking (RIBBI) and style bits",
       classification="Names / Style linking / RIBBI",
       what="name ID 2 is Regular, Italic, Bold or Bold Italic; non-RIBBI styles carry IDs 16/17; "
            "fsSelection and macStyle agree with ID 2",
       basis="OpenType spec, name IDs 1/2/16/17 and OS/2.fsSelection: Windows groups styles by ID 1 "
             "and links the four RIBBI styles by ID 2 and the style bits.",
       fix="Set ID 2 to one of the four RIBBI names, put the real style into IDs 16/17, "
           "and make fsSelection/macStyle match ID 2.",
       severity="medium", symptoms=(
           "Windows: Bold/Italic buttons switch to the wrong style or synthesize a fake one",))
def ribbi(v):
    id2 = v.names.get("2") or ""
    style = v.names.get("17") or id2
    if id2 not in RIBBI:
        yield Hit(key="name ID 2 is not RIBBI", measured=_quote(id2), expected="Regular, Italic, Bold or Bold Italic",
                  summary=f"name ID 2 is {_quote(id2)}")
    if style not in RIBBI and not (v.names.get("16") and v.names.get("17")):
        yield Hit(key="non-RIBBI style without IDs 16/17", measured=f"style {_quote(style)}, no ID 16/17",
                  expected="IDs 16 and 17 present", summary=f"style {_quote(style)} has no typographic names")
    sel = set(v.style.get("fs_selection") or [])
    mac = set(v.style.get("mac_style") or [])
    bold, italic = "Bold" in id2, "Italic" in id2
    wrong = []
    if ("BOLD" in sel) != bold:
        wrong.append("fsSelection BOLD")
    if ("ITALIC" in sel) != italic:
        wrong.append("fsSelection ITALIC")
    if ("REGULAR" in sel) != (id2 == "Regular"):
        wrong.append("fsSelection REGULAR")
    if ("Bold" in mac) != bold:
        wrong.append("macStyle Bold")
    if ("Italic" in mac) != italic:
        wrong.append("macStyle Italic")
    if id2 in RIBBI and wrong:
        yield Hit(key="style bits disagree with name ID 2", measured=", ".join(wrong) + f" (ID 2 {_quote(id2)})",
                  expected="bits match ID 2", summary="style bits disagree with name ID 2: " + ", ".join(wrong))


@check(id="names.wws", category="A", scope="file", applies=installable,
       title="WWS family names for styles with non-weight words",
       classification="Names / Windows family / WWS names",
       what="when ID 17 contains words other than weight, width or slope, IDs 21/22 are present "
            "and the WWS bit is clear",
       basis="OpenType spec, name IDs 21/22 and fsSelection bit 8.",
       fix="Add IDs 21/22 (family with the extra words, style with weight/width/slope only); clear fsSelection WWS.",
       severity="low", symptoms=("Windows font dialogs: the family splits into extra rows",))
def wws(v):
    style = v.names.get("17") or v.names.get("2") or ""
    extra = non_wws_words(style)
    sel = set(v.style.get("fs_selection") or [])
    if extra and not (v.names.get("21") and v.names.get("22")):
        yield Hit(key="IDs 21/22 missing", measured=f"style {_quote(style)} (extra: {', '.join(extra)})",
                  expected="IDs 21/22 present", summary=f"style {_quote(style)} has non-WWS words but no IDs 21/22")
    if extra and "WWS" in sel:
        yield Hit(key="WWS bit set on a non-WWS style", measured="fsSelection WWS set",
                  expected="WWS clear", summary="fsSelection WWS is set although the style has non-WWS words",
                  severity="medium")


@check(id="names.localized", category="A", scope="file", applies=installable,
       title="Localized name records are complete",
       classification="Names / Localized records / Missing IDs",
       what="every Windows language that has IDs 1/2 also has IDs 16/17 when English has them",
       basis="Applications pick the record set of the UI language; a language with IDs 1/2 but without "
             "16/17 makes the family look RIBBI-only there.",
       fix="Copy IDs 16 and 17 into every language that has IDs 1 and 2 (same values as English if not translated).",
       severity="high", symptoms=(
           "macOS in that language: Font Book shows the family under one style name with only Regular/Bold",))
def localized(v):
    records = v.facts.get("names", {}).get("records", {})
    english = set(records.get("3-1-0x409", []))
    for lang, ids in sorted(records.items()):
        if not lang.startswith("3-1-") or lang == "3-1-0x409":
            continue
        ids = set(ids)
        need = {i for i in (16, 17) if i in english} if ids & {1, 2} else set()
        missing = sorted(need - ids)
        if missing:
            yield Hit(key=f"{lang}: IDs {', '.join(map(str, missing))} missing",
                      measured=f"{lang} has IDs {', '.join(map(str, sorted(ids)))}",
                      expected=f"also IDs {', '.join(map(str, missing))}",
                      summary=f"language {lang} lacks IDs {', '.join(map(str, missing))}")


@check(id="names.unique", category="A", scope="package",
       title="Names are unique across the installable fonts",
       classification="Names / Uniqueness / Duplicate names",
       what="within each format (OTF, TTF), no two fonts share ID 1 + ID 2, ID 16 + ID 17, ID 4, ID 6 or ID 3",
       basis="Operating systems identify installed fonts by these names; duplicates replace each other "
             "or become unselectable (PostScript names too).",
       fix="Make the names distinct, e.g. add the lineage suffix (App) to every name the other lineage also uses.",
       severity="high", symptoms=("Windows, macOS: installing one font silently replaces another with the same name",))
def unique(views, ctx=None):
    keys = {
        "ID 1 + ID 2": lambda n: (n.get("1"), n.get("2")),
        "ID 16 + ID 17": lambda n: (n.get("16") or n.get("1"), n.get("17") or n.get("2")),
        "ID 4 (full name)": lambda n: n.get("4"),
        "ID 6 (PostScript name)": lambda n: n.get("6"),
        "ID 3 (unique ID)": lambda n: n.get("3"),
    }
    for fmt in ("OTF", "TTF"):
        vs = [v for v in views if v.ok and installable(v) and v.fmt == fmt]
        # variable fonts: the variations PostScript prefix (ID 25) and the instance PostScript names
        seen25 = defaultdict(list)
        for v in vs:
            if v.variable and v.names.get("25"):
                seen25[v.names["25"]].append(v)
        for value, dup in seen25.items():
            if len(dup) > 1:
                yield Hit(key="duplicate ID 25 (variations PostScript prefix)", files=files_of(dup),
                          measured=f"{_quote(value)} × {len(dup)}", expected="unique",
                          summary=f"{len(dup)} variable fonts share name ID 25 {_quote(value)}; their instances "
                                  f"get the same PostScript names")
        inst = defaultdict(set)
        for v in vs:
            for i in (v.facts.get("variation") or {}).get("instances", []):
                if i.get("postscript"):
                    inst[i["postscript"]].add(v.rel)
        clash = {ps: fs for ps, fs in inst.items() if len(fs) > 1}
        if clash:
            files = sorted(set().union(*clash.values()))
            yield Hit(key="duplicate instance PostScript names", files=files,
                      measured=f"{len(clash)} names, e.g. {_quote(next(iter(clash)))}", expected="unique",
                      summary=f"{len(clash)} named-instance PostScript names repeat across variable fonts")
        for label, get in keys.items():
            seen = defaultdict(list)
            for v in vs:
                seen[get(v.names)].append(v)
            for value, dup in seen.items():
                if len(dup) > 1 and value not in (None, (None, None)):
                    shown = " / ".join(x for x in value if x) if isinstance(value, tuple) else value
                    yield Hit(key=f"duplicate {label}", files=files_of(dup), measured=f"{_quote(shown)} × {len(dup)}",
                              expected="unique", summary=f"{len(dup)} {fmt} fonts share {label} {_quote(shown)}",
                              severity="medium" if label.startswith("ID 3") else None)


# ------------------------------------------------------------------ F

@check(id="names.required", category="F", scope="file", applies=installable,
       title="Required name records are present",
       classification="Names / Records / Required IDs",
       what="IDs 1, 2, 3, 4, 5, 6 exist for Windows English",
       basis="OpenType spec, name table: IDs 1–6 identify a font in every environment.",
       fix="Fill the missing names in the source and export again.", severity="high")
def required(v):
    missing = [i for i in ("1", "2", "3", "4", "5", "6") if not v.names.get(i)]
    if missing:
        yield Hit(key="IDs " + ", ".join(missing) + " missing", measured="missing: " + ", ".join(missing),
                  expected="IDs 1–6 present", summary="missing name IDs " + ", ".join(missing))


@check(id="names.postscript", category="F", scope="file", applies=installable,
       title="PostScript name is valid",
       classification="Names / PostScript name / Characters and length",
       what="ID 6 is at most 63 printable ASCII characters without spaces or []{}<>()/%",
       basis="OpenType spec, name ID 6; Adobe Technical Note #5902.",
       fix="Rename ID 6 to FamilyName-StyleName using only allowed characters.", severity="high")
def postscript(v):
    ps = v.names.get("6") or ""
    bad = sorted({c for c in ps if not (33 <= ord(c) <= 126) or c in "[](){}<>/%"})
    if bad or len(ps) > 63:
        why = []
        if bad:
            why.append("characters " + " ".join(repr(c) for c in bad))
        if len(ps) > 63:
            why.append(f"{len(ps)} characters")
        yield Hit(key="invalid PostScript name", measured=f"{_quote(ps)}: " + ", ".join(why),
                  expected="≤ 63 printable ASCII, no spaces", summary="PostScript name is invalid: " + ", ".join(why))


@check(id="names.full_name", category="F", scope="file", applies=installable,
       title="Full name length",
       classification="Names / Full name / Length",
       what="ID 4 is at most 63 characters", basis="Older Mac and Office code truncates full names past 63 characters.",
       fix="Shorten ID 4.", severity="low")
def full_name(v):
    full = v.names.get("4") or ""
    if len(full) > 63:
        yield Hit(key="full name over 63 characters", measured=f"{len(full)}: {_quote(full)}",
                  expected="≤ 63", summary=f"name ID 4 has {len(full)} characters")


@check(id="names.version", category="F", scope="file",
       title="Version string matches head.fontRevision",
       classification="Names / Version / ID 5 vs head",
       what="ID 5 starts with 'Version X.YYY' equal to head.fontRevision",
       basis="OpenType spec, name ID 5; installers compare head.fontRevision, people read ID 5.",
       fix="Set both from the same version number at export.", severity="low")
def version(v):
    id5 = v.names.get("5") or ""
    m = re.match(r"Version (\d+)\.(\d+)", id5)
    rev = v.style.get("revision")
    if not m:
        yield Hit(key="ID 5 not in 'Version X.YYY' form", measured=_quote(id5), expected="Version X.YYY",
                  summary=f"name ID 5 is {_quote(id5)}")
    elif rev is not None and abs(float(f"{m.group(1)}.{m.group(2)}") - float(rev)) > 0.0005:
        yield Hit(key="ID 5 ≠ head.fontRevision", measured=f"ID 5 {m.group(0)}, head {rev}",
                  expected="equal", summary=f"ID 5 says {m.group(1)}.{m.group(2)}, head.fontRevision is {rev}")


@check(id="names.mac_mirror", category="F", scope="file", applies=installable,
       title="Macintosh name records mirror Windows",
       classification="Names / Platform records / Mac vs Windows",
       what="where Mac (1,0,0) records exist, IDs 1, 2, 4, 6, 16, 17 equal the Windows English ones",
       basis="Old Mac apps read the Mac records; mismatches show different names on different platforms.",
       fix="Regenerate Mac records from the Windows ones or drop them.", severity="low", action="confirm")
def mac_mirror(v):
    mac = v.facts.get("names", {}).get("mac", {})
    if not mac:
        return
    diff = [i for i in ("1", "2", "4", "6", "16", "17") if i in mac and mac[i] != v.names.get(i)]
    if diff:
        yield Hit(key="Mac records differ", measured="; ".join(f"ID {i}: Mac {_quote(mac[i])} / Win {_quote(v.names.get(i))}" for i in diff),
                  expected="equal", summary="Mac name records differ for IDs " + ", ".join(diff))


@check(id="names.family_consistent", category="F", scope="family",
       title="Family-wide name fields agree",
       classification="Names / Family consistency / Shared fields",
       what="within a family and lineage: ID 16 family, version, vendor, copyright, trademark, manufacturer, "
            "designer, license and URLs are identical",
       basis="These fields describe the family, not the style; differences usually mean a style was exported "
             "from an older source.",
       fix="Export every style from the same source state.", severity="medium")
def family_consistent(group):
    if len(group) < 2:
        return
    fields = {"ID 16 / ID 1 family": lambda v: v.names.get("16") or v.names.get("1"),
              "ID 5 version": lambda v: (v.names.get("5") or "").split(";")[0],
              "vendor ID": lambda v: v.style.get("vendor"),
              "ID 0 copyright": lambda v: v.names.get("0"), "ID 7 trademark": lambda v: v.names.get("7"),
              "ID 8 manufacturer": lambda v: v.names.get("8"), "ID 9 designer": lambda v: v.names.get("9"),
              "ID 11 vendor URL": lambda v: v.names.get("11"), "ID 12 designer URL": lambda v: v.names.get("12"),
              "ID 13 license": lambda v: v.names.get("13"), "ID 14 license URL": lambda v: v.names.get("14")}
    for label, get in fields.items():
        values = defaultdict(list)
        for v in group:
            values[get(v)].append(v)
        if len(values) > 1:
            common = max(values, key=lambda k: len(values[k]))
            odd = [v for k, vs in values.items() if k != common for v in vs]
            shown = "; ".join(f"{_quote(str(k)[:60])} × {len(vs)}" for k, vs in values.items())
            yield Hit(key=f"{label} differs", files=files_of(odd), measured=shown, expected=f"one value ({_quote(str(common)[:60])})",
                      summary=f"{label} differs within the family")


PRIMARY_LANG = {"Hani": "zh-Hans", "Hira": "ja", "Kana": "ja", "Hang": "ko", "Arab": "ar", "Cyrl": "ru",
                "Grek": "el", "Hebr": "he", "Thai": "th", "Deva": "hi"}


@check(id="tables.meta", category="A", scope="file", applies=installable,
       title="Design and supported languages (meta table)",
       classification="Table structure / meta / dlng, slng",
       what="a font whose main script is not Latin has a meta table with dlng/slng",
       basis="Windows Settings and macOS pick preview text and language matching from meta dlng/slng; "
             "without it a CJK or Cyrillic font is previewed in English.",
       fix="Add a meta table with dlng and slng for the scripts the font is designed for.", severity="low",
       symptoms=("Windows Settings > Fonts: the preview shows English text instead of the font's own script",))
def meta(v):
    scripts = {k: n for k, n in v.facts["glyphs"]["scripts"].items() if k not in ("Zyyy", "Zinh", "Zzzz")}
    if not scripts:
        return
    main = max(scripts, key=scripts.get)
    if main != "Latn" and main in PRIMARY_LANG and "meta" not in v.facts.get("tables", []):
        latin_share = scripts.get("Latn", 0) / sum(scripts.values())
        multi = latin_share >= 0.25  # a multi-script family: the preview language is a choice, not a defect
        yield Hit(key="no meta table", measured=f"main script {main} ({scripts[main]} characters), Latin {latin_share:.0%}, no meta",
                  expected=f"meta dlng/slng ({PRIMARY_LANG[main]}" + (", Latn)" if multi else ")"),
                  summary=f"no meta table although the main script is {main}", action="confirm" if multi else None)
