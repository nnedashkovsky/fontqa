#!/usr/bin/env python3
"""Write the nine install-test fonts: one good font and eight with one fault each.

    python scripts/make_install_tests.py [folder]        (default: work/install-tests)

The fonts are generated, so nothing of a real font is touched. Install them one by one on macOS and Windows and
note the result in docs/install-matrix.md. Each file name starts with its number; the matrix uses the same numbers.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import fontkit as fk  # noqa: E402


def patch(path, tag, offset, data):
    """Overwrite bytes inside a table without recomputing anything: a hand edit."""
    raw = bytearray(open(path, "rb").read())
    for i in range(struct.unpack(">H", raw[4:6])[0]):
        t, _, off, _ = struct.unpack(">4sIII", raw[12 + 16 * i:28 + 16 * i])
        if t.decode("latin-1") == tag:
            raw[off + offset:off + offset + len(data)] = data
    open(path, "wb").write(raw)


def rewrite(path, fn):
    raw = bytearray(open(path, "rb").read())
    fn(raw)
    open(path, "wb").write(raw)


def main(out):
    def build(name, **kw):
        return fk.build(os.path.join(out, name), family="Install Test", **kw)

    build("00-good.ttf")
    build("01-bad-magic.ttf", mutate=lambda f: setattr(f["head"], "magicNumber", 0))
    build("02-no-name-table.ttf", mutate=lambda f: f.__delitem__("name"))
    build("03-no-cmap-table.ttf", mutate=lambda f: f.__delitem__("cmap"))
    patch(build("04-numglyphs-wrong.ttf"), "maxp", 4, b"\x03\xe7")
    path = build("05-truncated.ttf")
    rewrite(path, lambda raw: raw.__delitem__(slice(len(raw) - 300, None)))
    path = build("06-bad-version-tag.ttf")
    rewrite(path, lambda raw: raw.__setitem__(slice(0, 4), b"XXXX"))
    patch(build("07-bad-checksum.ttf"), "name", 0, b"\xff")
    path = build("08-glyf-with-OTTO-tag.otf")
    rewrite(path, lambda raw: raw.__setitem__(slice(0, 4), b"OTTO"))
    return sorted(os.listdir(out))


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "work", "install-tests")
    for name in main(folder):
        print(name)
