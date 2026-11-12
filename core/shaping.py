"""Shape fixed test strings through the uharfbuzz API.

In the terminal `uharfbuzz` is the real binding; in the browser `hbshim`
registers itself under that name and forwards to harfbuzzjs (WASM). The output
of this module is what proves the two agree: glyph ids, clusters, advances and
offsets for the same strings and fonts.
"""

import uharfbuzz as hb

# Kerning and spacing, ligatures, a mark sequence that needs `mark`/`ccmp`,
# fractions, and a locl case (Romanian comma accents).
STRINGS = [
    ("kern", "AVATAR Toffee Wavy LT", ""),
    ("liga", "office fluffy fjord", ""),
    ("marks", "é ä ñ ç ô", ""),
    ("frac", "1/2 3/4 10/25", "frac"),
    ("locl", "şţ șț", ""),
]


def shape_file(path, variations=None):
    with open(path, "rb") as fh:
        data = fh.read()
    face = hb.Face(hb.Blob(data))
    font = hb.Font(face)
    if variations:
        font.set_variations(variations)
    out = {}
    for key, text, features in STRINGS:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        feats = {f: True for f in features.split(",") if f}
        hb.shape(font, buf, feats)
        out[key] = [[i.codepoint, i.cluster, p.x_advance, p.y_advance, p.x_offset, p.y_offset]
                    for i, p in zip(buf.glyph_infos, buf.glyph_positions)]
    return out


def shape_files(paths):
    """`paths` are (abs, rel) pairs of sfnt files (HarfBuzz does not read WOFF)."""
    return {"strings": [list(s) for s in STRINGS],
            "files": [dict(path=rel, **shape_file(p)) for p, rel in paths]}
