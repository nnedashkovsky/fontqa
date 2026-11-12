"""Table values: OS/2, hhea, head, post (category F).

Values are compared with what the font itself implies (the weight word in the
style name, the bounding box, the cmap, the outlines of x and H) and with the
rest of the family. A font can be internally consistent and still differ from
its siblings, which is what breaks line spacing and style menus in a family.
"""

import math
from collections import defaultdict

from fontTools.ttLib.tables.O_S_2f_2 import intersectUnicodeRanges

from . import Hit, check, files_of, installable, static
from .names import WEIGHT_WORDS, WIDTH_WORDS, style_words

try:
    from fontTools.ttLib.tables.O_S_2f_2 import calcCodePageRanges
except ImportError:  # older fontTools
    calcCodePageRanges = None


def _style(v):
    return v.names.get("17") or v.names.get("2") or ""


def expected_weight(style):
    found = [WEIGHT_WORDS[w] for w in style_words(style) if w in WEIGHT_WORDS]
    return found[-1] if found else 400


def expected_width(style):
    found = [WIDTH_WORDS[w] for w in style_words(style) if w in WIDTH_WORDS]
    return found[-1] if found else 5


@check(id="os2.weight_class", category="F", scope="file", applies=lambda v: static(v) and installable(v),
       title="usWeightClass matches the style name",
       classification="Table values / OS/2 / usWeightClass",
       what="usWeightClass equals the class of the weight word in the style name (Light 300, Bold 700 …; none → 400)",
       basis="OpenType spec, OS/2.usWeightClass; Windows sorts and links styles by it.",
       fix="Set the weight class per style in the source (instance settings).", severity="medium")
def weight_class(v):
    style = _style(v)
    exp, got = expected_weight(style), v.style.get("weight_class")
    if got != exp:
        yield Hit(key=f"weight class ≠ style name", measured=f"{got} for {style!r}", expected=str(exp),
                  summary=f"usWeightClass {got}, style {style!r} implies {exp}",
                  action="confirm" if exp == 400 else None)


@check(id="os2.width_class", category="F", scope="file", applies=lambda v: static(v) and installable(v),
       title="usWidthClass matches the style name",
       classification="Table values / OS/2 / usWidthClass",
       what="usWidthClass is 5 unless the style name has a width word (Condensed, Expanded …)",
       basis="OpenType spec, OS/2.usWidthClass; Windows shows width words such as 'Semi-Expanded' "
             "next to styles that are not wider.",
       fix="Set usWidthClass to 5 for styles that are not width variants.", severity="medium", action="confirm",
       symptoms=("Windows font dialog: styles show width descriptors (Semi-Expanded, Expanded…)",))
def width_class(v):
    style = _style(v)
    exp, got = expected_width(style), v.style.get("width_class")
    if got != exp:
        yield Hit(key="width class ≠ style name", measured=f"{got} for {style!r}", expected=str(exp),
                  summary=f"usWidthClass {got}, style {style!r} implies {exp}")


@check(id="metrics.family_vertical", category="F", scope="family",
       title="Vertical metrics are the same across the family",
       classification="Table values / Vertical metrics / Family consistency",
       what="UPM, hhea, OS/2 typo and win metrics, USE_TYPO_METRICS and underline are the same for every style",
       basis="Different line metrics make lines jump when styles are mixed in one paragraph.",
       fix="Use one set of vertical metrics for the whole family (custom parameters at font level).",
       severity="medium", symptoms=("All applications: line spacing changes when a word is set in another style",))
def family_vertical(group):
    if len(group) < 2:
        return
    fields = {
        "UPM": lambda v: v.facts["metrics"]["upm"],
        "hhea ascender/descender/lineGap": lambda v: tuple(v.facts["metrics"]["hhea"]),
        "typo ascender/descender/lineGap": lambda v: tuple(v.facts["metrics"].get("typo") or ()),
        "win ascent/descent": lambda v: tuple(v.facts["metrics"].get("win") or ()),
        "USE_TYPO_METRICS": lambda v: "USE_TYPO_METRICS" in (v.style.get("fs_selection") or []),
        "underline position/thickness": lambda v: tuple(v.facts["metrics"]["underline"]),
    }
    for label, get in fields.items():
        values = defaultdict(list)
        for v in group:
            values[get(v)].append(v)
        if len(values) > 1:
            common = max(values, key=lambda k: len(values[k]))
            odd = [v for k, vs in values.items() if k != common for v in vs]
            yield Hit(key=f"{label} differ", files=files_of(odd),
                      measured="; ".join(f"{k} × {len(vs)}" for k, vs in values.items()),
                      expected=f"{common} everywhere", summary=f"{label} differ within the family",
                      severity="low" if label.startswith("underline") else None)


@check(id="metrics.win_clipping", category="F", scope="file",
       title="Nothing is clipped on Windows",
       classification="Table values / Vertical metrics / Clipping",
       what="usWinAscent ≥ head.yMax and usWinDescent ≥ −head.yMin",
       basis="Windows clips anything drawn outside usWinAscent/usWinDescent.",
       fix="Raise usWinAscent/usWinDescent to the font's bounding box.", severity="medium",
       symptoms=("Windows: tops of accented capitals or bottoms of descenders are cut off",))
def win_clipping(v):
    m = v.facts["metrics"]
    if not m.get("win"):
        return
    asc, desc = m["win"]
    ymin, ymax = m["bbox"][1], m["bbox"][3]
    if asc < ymax or desc < -ymin:
        yield Hit(key="glyphs exceed win metrics", measured=f"win {asc}/{desc}, bbox yMax {ymax} yMin {ymin}",
                  expected=f"win ≥ {ymax}/{-ymin}", summary=f"bbox {ymin}…{ymax} exceeds win {-desc}…{asc}")


@check(id="metrics.line_spacing", category="F", scope="file",
       title="Line spacing agrees between macOS and Windows",
       classification="Table values / Vertical metrics / Platform line spacing",
       what="hhea line height equals the Windows one (typo with USE_TYPO_METRICS, else win)",
       basis="macOS uses hhea, Windows uses win or typo metrics; a mismatch gives different leading per platform.",
       fix="Make hhea ascender − descender + lineGap equal to the metric Windows uses.", severity="low",
       action="confirm")
def line_spacing(v):
    m = v.facts["metrics"]
    if not m.get("typo"):
        return
    hhea = m["hhea"][0] - m["hhea"][1] + m["hhea"][2]
    use_typo = "USE_TYPO_METRICS" in (v.style.get("fs_selection") or [])
    win = m["typo"][0] - m["typo"][1] + m["typo"][2] if use_typo else m["win"][0] + m["win"][1]
    if abs(hhea - win) > m["upm"] * 0.01:
        yield Hit(key="hhea ≠ Windows line height", measured=f"hhea {hhea}, {'typo' if use_typo else 'win'} {win}",
                  expected="equal", summary=f"line height {hhea} on macOS vs {win} on Windows")


@check(id="metrics.use_typo", category="F", scope="file",
       title="USE_TYPO_METRICS is set",
       classification="Table values / OS/2 / USE_TYPO_METRICS",
       what="fsSelection bit 7 is set", basis="OpenType spec recommends the bit for new fonts; "
       "without it Windows uses win metrics, which also guard clipping and often give loose leading.",
       fix="Turn on 'Use Typo Metrics' in the source and keep typo metrics as the intended line spacing.",
       severity="low", action="confirm")
def use_typo(v):
    if "USE_TYPO_METRICS" not in (v.style.get("fs_selection") or []):
        yield Hit(key="USE_TYPO_METRICS off", measured="off", expected="on", summary="fsSelection USE_TYPO_METRICS is off")


@check(id="metrics.x_cap_height", category="F", scope="file", applies=lambda v: v.is_sfnt or v.fmt.startswith("WOFF"),
       title="Stated x-height and cap height match the drawing",
       classification="Table values / OS/2 / sxHeight, sCapHeight",
       what="sxHeight equals the top of x, sCapHeight the top of H (within 0.5% of UPM)",
       basis="OpenType spec, OS/2 version 2+; apps use them for small caps, superscripts and fallback sizing.",
       fix="Set x-height and cap height in the source masters to the drawn heights.", severity="low",
       action="confirm")
def x_cap_height(v):
    m = v.facts["metrics"]
    tol = m["upm"] * 0.005
    for label, cp, field in (("x-height", 0x78, "x_height"), ("cap height", 0x48, "cap_height")):
        stated = m.get(field)
        name = v.cmap.get(cp)
        if stated is None or name is None:
            continue
        b = v.bounds(name)
        if b and abs(b[3] - stated) > tol:
            yield Hit(key=f"{label} ≠ drawn", measured=f"OS/2 {stated}, drawn {round(b[3])}", expected=str(round(b[3])),
                      summary=f"OS/2 {label} {stated}, glyph {chr(cp)} reaches {round(b[3])}")


@check(id="os2.unicode_ranges", category="F", scope="file",
       title="Unicode range bits match the character set",
       classification="Table values / OS/2 / ulUnicodeRange",
       what="ulUnicodeRange bits equal the ones fontTools derives from the cmap",
       basis="OpenType spec, OS/2.ulUnicodeRange; Windows and Office use the bits for font fallback. "
             "Some clients ask for bits off on purpose — then confirm.",
       fix="Let the export compute the bits, or record why they differ.", severity="low", action="confirm")
def unicode_ranges(v):
    want = set(intersectUnicodeRanges(set(v.cmap)))
    have = set(v.facts["metrics"].get("unicode_ranges") or [])
    missing, extra = sorted(want - have), sorted(have - want)
    if missing or extra:
        parts = ([f"off but used: {missing}"] if missing else []) + ([f"on but unused: {extra}"] if extra else [])
        yield Hit(key="range bits differ from cmap", measured="; ".join(parts), expected=f"bits {sorted(want)}",
                  summary="ulUnicodeRange " + "; ".join(parts))


@check(id="os2.codepage_ranges", category="F", scope="file",
       title="Code page bits match the character set",
       classification="Table values / OS/2 / ulCodePageRange",
       what="ulCodePageRange bits equal the ones fontTools derives from the cmap",
       basis="OpenType spec, OS/2.ulCodePageRange; Windows uses them to decide which scripts a font supports.",
       fix="Let the export compute the bits.", severity="low", action="confirm",
       applies=lambda v: calcCodePageRanges is not None)
def codepage_ranges(v):
    want = set(calcCodePageRanges(set(v.cmap)))
    have = set(v.facts["metrics"].get("codepage_ranges") or [])
    missing, extra = sorted(want - have), sorted(have - want)
    if missing or extra:
        parts = ([f"off but supported: {missing}"] if missing else []) + ([f"on but not supported: {extra}"] if extra else [])
        yield Hit(key="code page bits differ from cmap", measured="; ".join(parts), expected=f"bits {sorted(want)}",
                  summary="ulCodePageRange " + "; ".join(parts))


@check(id="post.italic", category="F", scope="file",
       title="Italic angle, caret and italic bit agree",
       classification="Table values / post, hhea / Italic angle and caret",
       what="italic fonts have a non-zero italicAngle, upright fonts zero; the caret slope follows the angle",
       basis="OpenType spec, post.italicAngle and hhea.caretSlopeRise/Run; apps slant the cursor and "
             "selection by them.",
       fix="Set the italic angle in the source masters; the export derives the caret from it.", severity="low")
def italic(v):
    angle = v.style.get("italic_angle") or 0
    rise, run, _ = v.facts["metrics"]["caret"]
    if v.italic and angle == 0:
        yield Hit(key="italic with angle 0", measured="italicAngle 0", expected="non-zero",
                  summary="italic font has italicAngle 0", action="confirm")
    if not v.italic and angle != 0 and "OBLIQUE" not in (v.style.get("fs_selection") or []):
        yield Hit(key="slanted but not marked italic", measured=f"italicAngle {angle}", expected="ITALIC bit or angle 0",
                  summary=f"italicAngle {angle} without the italic bit", severity="medium", action="confirm")
    if angle and rise:
        caret = math.degrees(math.atan2(run, rise))
        if abs(caret + angle) > 1:
            yield Hit(key="caret slope ≠ italic angle", measured=f"caret {caret:.1f}°, angle {angle}°",
                      expected=f"caret {-angle}°", summary=f"caret slope {caret:.1f}° vs italic angle {angle}°")


@check(id="post.format", category="F", scope="file", applies=lambda v: v.lineage == "Web" and v.facts.get("outline") == "glyf",
       title="Web fonts without glyph names",
       classification="Table values / post / Format",
       what="TrueType web fonts use post format 3 (no glyph names)",
       basis="Glyph names in post 2.0 only add bytes to a web font; browsers never read them "
             "(usually harmless).",
       fix="Drop glyph names from the web build (post format 3).", severity="low", action="ok")
def post_format(v):
    fmt = v.facts["metrics"].get("post_format")
    if fmt == 2:
        yield Hit(key="post format 2 in web fonts", measured="post 2.0 with glyph names", expected="post 3.0",
                  summary="web font keeps glyph names (post 2.0)")


@check(id="tables.hinting", category="F", scope="file", applies=lambda v: v.facts.get("outline") == "glyf",
       title="TrueType hinting tables are present",
       classification="Table values / Hinting / fpgm, prep, cvt",
       what="TrueType fonts carry hinting tables, or at least a prep program that turns on dropout control",
       basis="Without hinting, Windows GDI renders small sizes unevenly; without dropout control thin "
             "strokes can vanish at low resolutions (usually harmless for display use).",
       fix="Autohint (ttfautohint) or add a minimal prep with dropout control at export.", severity="low", action="ok")
def hinting(v):
    tables = set(v.facts.get("tables", []))
    missing = [t for t in ("fpgm", "prep", "cvt ") if t not in tables]
    if missing:
        yield Hit(key="no hinting tables", measured="missing " + ", ".join(t.strip() for t in missing),
                  expected="fpgm, prep, cvt", summary="unhinted: no " + ", ".join(t.strip() for t in missing))
