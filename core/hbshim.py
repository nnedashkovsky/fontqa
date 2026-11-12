"""A stand-in for `uharfbuzz` in the browser, forwarding to harfbuzzjs (WASM).

Pyodide has no uharfbuzz build, yet both Hyperglot and Font Bakery shape text
through it. Rather than lose those checks in the browser, this module provides
the small part of the uharfbuzz API they touch and runs it on harfbuzzjs, which
the worker loads as `self.hb`. `install()` registers it as `uharfbuzz` in
sys.modules, so their imports pick it up unchanged.

harfbuzzjs is built with HB_TINY: no glyph names, so names and nominal glyphs
come from fontTools instead. Anything not implemented raises NotImplementedError
naming the missing call, which the probes report as "needs native HarfBuzz".
"""

import io
import sys

from fontTools.ttLib import TTFont


def _hbjs():
    import js
    return js.hb


def _to_arraybuffer(data):
    import js
    from pyodide.ffi import to_js
    return js.Uint8Array.new(to_js(bytes(data))).buffer


class Blob:
    def __init__(self, data=b""):
        self.data = bytes(data)
        self._js = _hbjs().createBlob(_to_arraybuffer(self.data))

    @classmethod
    def from_file_path(cls, path):
        with open(path, "rb") as fh:
            return cls(fh.read())


class Face:
    def __init__(self, blob, index=0):
        if isinstance(blob, (bytes, bytearray)):
            blob = Blob(blob)
        self.blob = blob
        self._js = _hbjs().createFace(blob._js, index)

    @property
    def upem(self):
        return int(self._js.upem)


class Font:
    def __init__(self, face):
        self.face = face
        self._js = _hbjs().createFont(face._js)
        self._tt = None

    def _font(self):
        if self._tt is None:
            self._tt = TTFont(io.BytesIO(self.face.blob.data), lazy=True)
        return self._tt

    def set_variations(self, variations):
        from pyodide.ffi import to_js
        import js
        self._js.setVariations(to_js(dict(variations), dict_converter=js.Object.fromEntries))

    def get_glyph_name(self, gid):
        order = self._font().getGlyphOrder()
        return order[gid] if 0 <= gid < len(order) else None

    def get_nominal_glyph(self, codepoint):
        name = (self._font().getBestCmap() or {}).get(codepoint)
        return self._font().getGlyphID(name) if name is not None else None

    get_glyph = get_nominal_glyph

    def __getattr__(self, name):
        raise NotImplementedError(f"uharfbuzz.Font.{name} (not in the harfbuzzjs shim)")


class GlyphInfo:
    __slots__ = ("codepoint", "cluster", "flags")

    def __init__(self, g, cl, flags=0):
        self.codepoint, self.cluster, self.flags = g, cl, flags


class GlyphPosition:
    __slots__ = ("x_advance", "y_advance", "x_offset", "y_offset")

    def __init__(self, ax, ay, dx, dy):
        self.x_advance, self.y_advance, self.x_offset, self.y_offset = ax, ay, dx, dy

    @property
    def position(self):
        return (self.x_offset, self.y_offset, self.x_advance, self.y_advance)


class Buffer:
    def __init__(self):
        self._text = ""
        self._guess = False
        self.direction = self.script = self.language = None
        self.cluster_level = None
        self._flat, self._infos, self._positions = [], None, None

    # built on first access: callers of our own read `rows(buf)` straight from the flat array,
    # and five million GlyphInfo/GlyphPosition objects were half the shaping time in the browser
    @property
    def glyph_infos(self):
        if self._infos is None:
            f = self._flat
            self._infos = [GlyphInfo(g, cl) for g, cl in zip(f[0::6], f[1::6])]
        return self._infos

    @property
    def glyph_positions(self):
        if self._positions is None:
            f = self._flat
            self._positions = [GlyphPosition(*r) for r in zip(f[2::6], f[3::6], f[4::6], f[5::6])]
        return self._positions

    def _set(self, flat, infos=None, positions=None):
        self._flat, self._infos, self._positions = flat, infos, positions

    def add_str(self, text, item_offset=0, item_length=-1):
        self._text += text

    def add_codepoints(self, codepoints, item_offset=0, item_length=-1):
        self._text += "".join(chr(c) for c in codepoints)

    def guess_segment_properties(self):
        self._guess = True

    def clear_contents(self):
        self._text = ""
        self._set([])

    def __len__(self):
        return len(self._flat) // 6 if self._infos is None else len(self._infos)


def _feature_string(features):
    if not features:
        return ""
    parts = []
    for tag, value in features.items():
        if value is True:
            parts.append(tag)
        elif value is False:
            parts.append("-" + tag)
        else:
            parts.append(f"{tag}={int(value)}")
    return ",".join(parts)


def shape(font, buffer, features=None, shapers=None):
    hb = _hbjs()
    b = hb.createBuffer()
    try:
        b.addText(buffer._text)
        if buffer.direction:
            b.setDirection(buffer.direction)
        if buffer.script:
            b.setScript(buffer.script)
        if buffer.language:
            b.setLanguage(buffer.language)
        if buffer.cluster_level is not None:
            b.setClusterLevel(buffer.cluster_level)
        if buffer._guess or not (buffer.direction and buffer.script):
            b.guessSegmentProperties()
        hb.shape(font._js, b, _feature_string(features))
        import js
        flat = list(js.hbFlat(b).to_py()) if hasattr(js, "hbFlat") else None
        glyphs = None if flat is not None else b.json().to_py()
    finally:
        b.destroy()
    if flat is not None:
        buffer._set(flat)
        return
    buffer._set([x for g in glyphs for x in (g["g"], g["cl"], g["ax"], g["ay"], g["dx"], g["dy"])],
                [GlyphInfo(g["g"], g["cl"], g.get("flags", 0)) for g in glyphs],
                [GlyphPosition(g["ax"], g["ay"], g["dx"], g["dy"]) for g in glyphs])


def rows(buf):
    """(glyph id, cluster, x_advance, y_advance, x_offset, y_offset) per glyph of a shaped buffer,
    from the real uharfbuzz or from this shim (sliced straight out of its flat array)."""
    flat = getattr(buf, "_flat", None)
    if flat is not None:
        return list(zip(flat[0::6], flat[1::6], flat[2::6], flat[3::6], flat[4::6], flat[5::6]))
    return [(i.codepoint, i.cluster, p.x_advance, p.y_advance, p.x_offset, p.y_offset)
            for i, p in zip(buf.glyph_infos, buf.glyph_positions)]


def version_string():
    return str(_hbjs().version_string())


def install():
    """Register this module as `uharfbuzz` (no-op in the terminal)."""
    if "uharfbuzz" in sys.modules and sys.modules["uharfbuzz"] is not sys.modules[__name__]:
        return sys.modules["uharfbuzz"]
    mod = sys.modules[__name__]
    sys.modules["uharfbuzz"] = mod
    return mod


__all__ = ["Blob", "Face", "Font", "Buffer", "shape", "rows", "version_string", "install"]
