"""Facts about one font file: everything later checks need, read once.

Checks never open a TTFont themselves; they read this plain dict. Being plain
JSON, the facts can be cached in the browser (IndexedDB, keyed by sha256 and
core version), compared between the browser and the terminal run, and diffed
between two builds. So the output must be deterministic: no floats with noise,
no object reprs, every mapping keyed by strings.

Only the binary is read; the source .glyphs file is a later phase.
"""

import hashlib
import io
from collections import Counter

from fontTools import unicodedata as ucd
from fontTools.ttLib import TTFont

FONT_EXTENSIONS = (".otf", ".ttf", ".woff", ".woff2", ".ttc", ".otc")

WIN_EN = (3, 1, 0x409)
MAC_EN = (1, 0, 0)

FS_SELECTION = {
    0: "ITALIC", 1: "UNDERSCORE", 2: "NEGATIVE", 3: "OUTLINED", 4: "STRIKEOUT",
    5: "BOLD", 6: "REGULAR", 7: "USE_TYPO_METRICS", 8: "WWS", 9: "OBLIQUE",
}
MAC_STYLE = {0: "Bold", 1: "Italic", 2: "Underline", 3: "Outline", 4: "Shadow",
             5: "Condensed", 6: "Extended"}
VARIATION_TABLES = ("STAT", "avar", "cvar", "gvar", "HVAR", "MVAR", "VVAR")


def sniff_format(data):
    """Container format from the first four bytes, not from the file name."""
    sig = data[:4]
    if sig == b"wOFF":
        return "WOFF"
    if sig == b"wOF2":
        return "WOFF2"
    if sig == b"ttcf":
        return "TTC"
    if sig == b"OTTO":
        return "OTF"
    if sig in (b"\x00\x01\x00\x00", b"true"):
        return "TTF"
    return None


def _num(v):
    """Ints stay ints; floats are rounded so 1.2000000476 and 1.2 compare equal."""
    if isinstance(v, float):
        r = round(v, 3)
        return int(r) if r == int(r) else r
    return v


def _bits(value, names):
    return [names[b] for b in sorted(names) if value & (1 << b)]


def _set_bits(value, width):
    return [b for b in range(width) if value >> b & 1]


def file_facts(path, relpath, data=None):
    """Facts for one file. Unreadable files still get size, hash and an error."""
    if data is None:
        with open(path, "rb") as fh:
            data = fh.read()
    out = {
        "path": relpath,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format": sniff_format(data),
    }
    if out["format"] is None:
        out["error"] = "not a font file"
        return out
    if out["format"] == "TTC":
        out["error"] = "font collections are not supported yet"
        return out
    try:
        font = TTFont(io.BytesIO(data), lazy=True)
        out.update(font_facts(font))
    except Exception as exc:  # a broken font is a finding, not a crash
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def font_facts(font):
    tables = sorted(font.reader.keys())
    facts = {
        "tables": tables,
        "outline": ("CFF2" if "CFF2" in tables else "CFF" if "CFF " in tables
                    else "glyf" if "glyf" in tables else None),
        "names": _names(font),
    }
    win = facts["names"]["windows"]
    facts["style"] = _style(font, win)
    facts["metrics"] = _metrics(font)
    facts["glyphs"] = _glyphs(font)
    facts["layout"] = {tag: _layout(font, tag) for tag in ("GSUB", "GPOS") if tag in font}
    facts["layout"]["kern_pairs"] = _legacy_kern_pairs(font)
    facts["variation"] = _variation(font) if "fvar" in font else None
    return facts


def _names(font):
    """English Windows and Mac strings, plus which IDs exist per platform/language."""
    windows, mac, records = {}, {}, {}
    if "name" not in font:
        return {"windows": windows, "mac": mac, "records": {}}
    for rec in font["name"].names:
        key = f"{rec.platformID}-{rec.platEncID}-0x{rec.langID:X}"
        records.setdefault(key, set()).add(rec.nameID)
        ident = (rec.platformID, rec.platEncID, rec.langID)
        if ident not in (WIN_EN, MAC_EN):
            continue
        try:
            text = rec.toUnicode()
        except Exception:
            text = None
        (windows if ident == WIN_EN else mac)[str(rec.nameID)] = text
    return {"windows": windows, "mac": mac, "records": {k: sorted(v) for k, v in sorted(records.items())}}


def _style(font, win):
    os2 = font["OS/2"] if "OS/2" in font else None
    head, post = font["head"], font["post"]
    return {
        "family": win.get("16") or win.get("1"),
        "subfamily": win.get("17") or win.get("2"),
        "weight_class": os2.usWeightClass if os2 else None,
        "width_class": os2.usWidthClass if os2 else None,
        "fs_selection": _bits(os2.fsSelection, FS_SELECTION) if os2 else None,
        "mac_style": _bits(head.macStyle, MAC_STYLE),
        "italic_angle": _num(post.italicAngle),
        "fixed_pitch": bool(post.isFixedPitch),
        "fs_type": os2.fsType if os2 else None,
        "vendor": os2.achVendID if os2 else None,
        "revision": _num(round(head.fontRevision, 3)),
    }


def _metrics(font):
    head, hhea = font["head"], font["hhea"]
    m = {
        "upm": head.unitsPerEm,
        "bbox": [head.xMin, head.yMin, head.xMax, head.yMax],
        "head_flags": head.flags,
        "lowest_rec_ppem": head.lowestRecPPEM,
        "hhea": [hhea.ascent, hhea.descent, hhea.lineGap],
        "caret": [hhea.caretSlopeRise, hhea.caretSlopeRun, hhea.caretOffset],
        "underline": [font["post"].underlinePosition, font["post"].underlineThickness],
        "post_format": _num(font["post"].formatType),
    }
    if "OS/2" in font:
        os2 = font["OS/2"]
        m["os2_version"] = os2.version
        m["typo"] = [os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap]
        m["win"] = [os2.usWinAscent, os2.usWinDescent]
        m["x_height"] = getattr(os2, "sxHeight", None)
        m["cap_height"] = getattr(os2, "sCapHeight", None)
        m["strikeout"] = [os2.yStrikeoutPosition, os2.yStrikeoutSize]
        m["unicode_ranges"] = sorted(os2.getUnicodeRanges())
        m["codepage_ranges"] = (_set_bits(getattr(os2, "ulCodePageRange1", 0), 32)
                                + [32 + b for b in _set_bits(getattr(os2, "ulCodePageRange2", 0), 32)])
        m["panose"] = [getattr(os2.panose, a) for a in (
            "bFamilyType", "bSerifStyle", "bWeight", "bProportion", "bContrast",
            "bStrokeVariation", "bArmStyle", "bLetterForm", "bMidline", "bXHeight")]
    return m


def _glyphs(font):
    cmap = font.getBestCmap() or {}
    order = font.getGlyphOrder()
    scripts, blocks = Counter(), Counter()
    for cp in cmap:
        ch = chr(cp)
        scripts[ucd.script(ch)] += 1
        blocks[ucd.block(ch)] += 1
    encoded = set(cmap.values())
    return {
        "count": len(order),
        "cmap": len(cmap),
        "unencoded": sum(1 for g in order if g not in encoded),
        "notdef_first": bool(order) and order[0] == ".notdef",
        "scripts": dict(sorted(scripts.items())),
        "blocks": dict(sorted(blocks.items())),
    }


def _layout(font, tag):
    table = font[tag].table
    scripts = {}
    if table.ScriptList:
        for rec in table.ScriptList.ScriptRecord:
            langs = ["dflt"] if rec.Script.DefaultLangSys else []
            langs += [lr.LangSysTag.strip() for lr in rec.Script.LangSysRecord]
            scripts[rec.ScriptTag.strip()] = langs
    features = sorted({fr.FeatureTag for fr in table.FeatureList.FeatureRecord}) if table.FeatureList else []
    lookups = len(table.LookupList.Lookup) if table.LookupList else 0
    return {"scripts": dict(sorted(scripts.items())), "features": features, "lookups": lookups}


def _legacy_kern_pairs(font):
    if "kern" not in font:
        return None
    return sum(len(getattr(sub, "kernTable", {})) for sub in font["kern"].kernTables)


def _variation(font):
    name = font["name"]
    fvar = font["fvar"]
    axes = [{
        "tag": a.axisTag, "min": _num(a.minValue), "default": _num(a.defaultValue),
        "max": _num(a.maxValue), "name": name.getDebugName(a.axisNameID),
    } for a in fvar.axes]
    instances = [{
        "name": name.getDebugName(i.subfamilyNameID),
        "postscript": name.getDebugName(i.postscriptNameID) if i.postscriptNameID not in (None, 0xFFFF) else None,
        "coordinates": {k: _num(v) for k, v in sorted(i.coordinates.items())},
    } for i in fvar.instances]
    return {"axes": axes, "instances": instances,
            "tables": [t for t in VARIATION_TABLES if t in font]}
