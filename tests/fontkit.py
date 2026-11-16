"""Test fonts made by code: a clean specimen and broken copies of it.

No font files live in the repository. `build()` writes a small font with the
Western European set, drawn as boxes, whose tables satisfy every check; each
test then breaks one thing (a name, a width, a bit) and expects one check to
fire. The fonts are not meant to be looked at.
"""

import os
from array import array

from fontTools.fontBuilder import FontBuilder
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables import ttProgram

UPM, CAP, XH, ASC, DESC, GAP = 1000, 700, 500, 800, -200, 200
WIDTH, SPACE = 600, 300
BLANK = {0x20, 0xA0, 0xAD}


def western():
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "core", "data", "charsets.json"), encoding="utf-8") as fh:
        return sorted(json.load(fh)["Western European (cp1252)"])


def gname(cp):
    return "space" if cp == 0x20 else f"uni{cp:04X}"


def box(pen, top, left=50, right=550, bottom=0):
    pen.moveTo((left, bottom))
    pen.lineTo((left, top))
    pen.lineTo((right, top))
    pen.lineTo((right, bottom))
    pen.closePath()


def height(cp):
    return XH if chr(cp).islower() else CAP


def build(path, family="Test Sans", style="Regular", *, chars=None, widths=None, empty=(), shapes=None,
          extra_glyphs=None, fea=None, cff=False, names=None, os2=None, version=1.0, mutate=None,
          flavor=None, post_names=True, hinted=True, typo_names=True):
    """Write one font. Returns the path.

    chars         codepoints (default: the Western European set)
    widths        {codepoint or glyph name: advance}
    empty         codepoints whose glyph gets no outline
    shapes        {codepoint or glyph name: function(pen)} to draw something else
    extra_glyphs  {glyph name: (advance, top)} unencoded glyphs (alternates)
    fea           feature code compiled into GSUB/GPOS
    names, os2    overrides for name records (by FontBuilder key) and OS/2 fields
    mutate        function(TTFont) run just before saving
    """
    chars = sorted(chars if chars is not None else western())
    widths, shapes, extra_glyphs = dict(widths or {}), dict(shapes or {}), dict(extra_glyphs or {})
    bold, italic = "Bold" in style, "Italic" in style
    ribbi = style in ("Regular", "Italic", "Bold", "Bold Italic")
    order = [".notdef"] + [gname(c) for c in chars] + list(extra_glyphs)
    cmap = {c: gname(c) for c in chars}

    def advance(key, name):
        if key in widths:
            return widths[key]
        if name in widths:
            return widths[name]
        return SPACE if key in BLANK else WIDTH

    metrics, tops = {".notdef": WIDTH}, {".notdef": CAP}
    for c in chars:
        metrics[gname(c)] = advance(c, gname(c))
        tops[gname(c)] = None if (c in BLANK or c in empty) else height(c)
    for name, (adv, top) in extra_glyphs.items():
        metrics[name] = widths.get(name, adv)
        tops[name] = top

    def draw(name, pen):
        key = next((c for c in chars if gname(c) == name), name)
        if key in shapes:
            shapes[key](pen)
        elif name in shapes:
            shapes[name](pen)
        elif tops[name] is not None:
            box(pen, tops[name])

    fb = FontBuilder(UPM, isTTF=not cff)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    if cff:
        charstrings = {}
        for name in order:
            pen = T2CharStringPen(metrics[name], None, roundTolerance=0)  # keep fractions when a test asks for them
            draw(name, pen)
            charstrings[name] = pen.getCharString()
        ps = (family + "-" + style).replace(" ", "")
        fb.setupCFF(ps, {"FullName": f"{family} {style}"}, charstrings, {})
        lsb = {n: 50 if tops[n] is not None else 0 for n in order}
    else:
        glyphs = {}
        for name in order:
            pen = TTGlyphPen(None)
            draw(name, pen)
            glyphs[name] = pen.glyph()
        fb.setupGlyf(glyphs)
        lsb = {n: (glyphs[n].xMin if glyphs[n].numberOfContours else 0) for n in order}
    fb.setupHorizontalMetrics({n: (metrics[n], lsb[n]) for n in order})
    fb.setupHorizontalHeader(ascent=ASC, descent=DESC, lineGap=GAP)

    ps = (family + "-" + style).replace(" ", "")
    rec = {
        "copyright": "Copyright 2026 Test Foundry", "manufacturer": "Test Foundry", "designer": "A. Tester",
        "vendorURL": "https://example.com", "designerURL": "https://example.com/tester",
        "licenseDescription": "Test licence.", "licenseInfoURL": "https://example.com/licence",
        "uniqueFontIdentifier": f"1.000;TEST;{ps}", "fullName": f"{family} {style}", "psName": ps,
        "version": f"Version {version:.3f}",
    }
    if ribbi:
        rec.update(familyName=family, styleName=style)
    else:  # e.g. Light: linked as "Family Light" + Regular, real names in 16/17
        rec.update(familyName=f"{family} {style}", styleName="Regular")
        if typo_names:
            rec.update(typographicFamily=family, typographicSubfamily=style)
    rec.update(names or {})
    fb.setupNameTable({k: v for k, v in rec.items() if v is not None}, mac=False)

    sel = 0x80 | (0x20 if bold and ribbi else 0) | (0x01 if italic and ribbi else 0)
    if not (sel & 0x21):
        sel |= 0x40
    weight = {"Light": 300, "Regular": 400, "Medium": 500, "Bold": 700, "Black": 900}
    fields = dict(sTypoAscender=ASC, sTypoDescender=DESC, sTypoLineGap=GAP, usWinAscent=ASC, usWinDescent=-DESC,
                  sxHeight=XH, sCapHeight=CAP, achVendID="TEST", fsSelection=sel, version=4, usWidthClass=5,
                  usWeightClass=next((w for k, w in weight.items() if k in style), 400))
    fields.update(os2 or {})
    fb.setupOS2(**fields)
    fb.setupPost(keepGlyphNames=post_names, underlinePosition=-100, underlineThickness=50)
    font = fb.font
    font["head"].fontRevision = version
    font["head"].macStyle = (1 if sel & 0x20 else 0) | (2 if sel & 0x01 else 0)
    font["OS/2"].recalcUnicodeRanges(font)
    font["OS/2"].recalcCodePageRanges(font)
    if fea:
        addOpenTypeFeaturesFromString(font, fea)
    if hinted and not cff:
        for tag in ("fpgm", "prep"):
            font[tag] = table = newTable(tag)
            table.program = ttProgram.Program()
            table.program.fromBytecode(b"\xb8\x01\xff\x85\xb0\x04\x8d")
        font["cvt "] = cvt = newTable("cvt ")
        cvt.values = array("h", [0])
    if mutate:
        mutate(font)
    if flavor:
        font.flavor = flavor
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    font.save(path)
    return path


def family(folder, styles=("Regular", "Bold"), name="Test Sans", web=True, line="Desktop", ext=".ttf",
           per_style=None, **kw):
    """A small clean family: fonts named after their PostScript names in <line>/, WOFF2 copies in Web/.

    per_style maps a style to extra build() arguments for that style only.
    """
    out = []
    for style in styles:
        ps = (name + "-" + style).replace(" ", "")
        args = dict(kw, **(per_style or {}).get(style, {}))
        out.append(build(os.path.join(folder, line, ps + ext), name, style, cff=ext == ".otf", **args))
        if web:
            out.append(build(os.path.join(folder, "Web", ps + ".woff2"), name, style, cff=ext == ".otf",
                             flavor="woff2", post_names=False, **args))
    return out


def bold_box(pen, top=CAP):
    box(pen, top, left=30, right=570)


def variable(folder, name="Test Var", line="App", statics=True, mutate=None, bold_shapes=None, static_bold=None):
    """A weight-axis variable font (Regular 400 … Bold 700) with its two statics in <line>/.

    The Bold master is drawn wider; the static Bold is the same drawing, so the
    instances match the statics. `bold_shapes` redraws glyphs of the Bold master only;
    `static_bold` passes extra build() arguments to the static Bold.
    """
    from fontTools import varLib
    from fontTools.designspaceLib import (AxisDescriptor, AxisLabelDescriptor, DesignSpaceDocument,
                                          InstanceDescriptor, SourceDescriptor)
    chars = western()
    bold = {c: (lambda pen, c=c: bold_box(pen, height(c))) for c in chars if c not in BLANK}
    masters = os.path.join(folder, "_masters")
    reg = build(os.path.join(masters, "Regular.ttf"), name + " VF", "Regular")
    bd = build(os.path.join(masters, "Bold.ttf"), name + " VF", "Bold", shapes={**bold, **(bold_shapes or {})})
    ds = DesignSpaceDocument()
    ds.formatVersion = "5.0"  # axis labels (STAT) are a format 5 feature
    axis = AxisDescriptor()
    axis.name, axis.tag, axis.minimum, axis.default, axis.maximum = "Weight", "wght", 400, 400, 700
    axis.axisLabels = [AxisLabelDescriptor(name="Regular", userValue=400, elidable=True),
                       AxisLabelDescriptor(name="Bold", userValue=700)]
    ds.addAxis(axis)
    for path, value in ((reg, 400), (bd, 700)):
        src = SourceDescriptor()
        src.path, src.location = path, {"Weight": value}
        ds.addSource(src)
    for style, value in (("Regular", 400), ("Bold", 700)):
        inst = InstanceDescriptor()
        inst.familyName, inst.styleName, inst.location = name + " VF", style, {"Weight": value}
        inst.postScriptFontName = (name + "VF-" + style).replace(" ", "")
        ds.addInstance(inst)
    font, _, _ = varLib.build(ds)
    from fontTools.otlLib.builder import buildStatTable
    buildStatTable(font, [dict(tag="wght", name="Weight", values=[
        dict(value=400, name="Regular", flags=0x2), dict(value=700, name="Bold")])], elidedFallbackName=2)
    ps = (name + "VF").replace(" ", "")
    for nid, text in ((3, f"1.000;TEST;{ps}"), (4, name + " VF"), (6, ps)):
        set_name(font, nid, text)
    if mutate:
        mutate(font)
    out = [os.path.join(folder, line, ps + ".ttf")]
    os.makedirs(os.path.dirname(out[0]), exist_ok=True)
    font.save(out[0])
    import shutil
    shutil.rmtree(masters)
    if statics:
        out += family(folder, name=name, line=line, per_style={"Bold": dict({"shapes": bold}, **(static_bold or {}))})
    return out


def set_name(font, name_id, text, lang=0x409):
    font["name"].setName(text, name_id, 3, 1, lang)


def drop_name(font, name_id):
    font["name"].names = [n for n in font["name"].names if n.nameID != name_id]
