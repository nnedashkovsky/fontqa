#!/usr/bin/env python3
"""Build core/data/charsets.json.

    git clone --depth 1 --filter=blob:none --sparse https://github.com/googlefonts/glyphsets.git gfsets
    (cd gfsets && git sparse-checkout set --skip-checks data/results/nam LICENSE)
    python scripts/build_charsets.py gfsets

Taken from:
  ASCII, ISO 8859-1, Windows 1250–1258   Python's codecs: the printable characters of the code page
  Adobe Latin 1–5                        the lists already in charsets.json (adobe-type-tools, MIT)
  Google Fonts glyphsets                 data/results/nam/GF_*.nam (googlefonts/glyphsets, Apache-2.0)
The Google Fonts sets are layered: Latin Plus and Greek Plus / Pro hold only what they add to Core.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from core import charsets as cs  # noqa: E402

TARGET = os.path.join(HERE, "..", "core", "data", "charsets.json")

WINDOWS = [("Central European (cp1250)", "cp1250", "Latn"), ("Cyrillic (cp1251)", "cp1251", "Cyrl"),
           ("Western European (cp1252)", "cp1252", "Latn"), ("Greek (cp1253)", "cp1253", "Grek"),
           ("Turkish (cp1254)", "cp1254", "Latn"), ("Hebrew (cp1255)", "cp1255", "Hebr"),
           ("Arabic (cp1256)", "cp1256", "Arab"), ("Baltic (cp1257)", "cp1257", "Latn"),
           ("Vietnamese (cp1258)", "cp1258", "Latn")]
GOOGLE = [("GF_Latin_Kernel", "Latn", "the least a Latin font needs: basic letters, digits and punctuation"),
          ("GF_Latin_Core", "Latn", "Western, Central and Northern European languages"),
          ("GF_Latin_Plus", "Latn", "adds currencies, math and fractions to Core (only the additions)"),
          ("GF_Latin_African", "Latn", "African Latin alphabets"),
          ("GF_Latin_Vietnamese", "Latn", "Vietnamese"),
          ("GF_Cyrillic_Core", "Cyrl", "the main Cyrillic languages"),
          ("GF_Cyrillic_Plus", "Cyrl", "more Cyrillic languages"),
          ("GF_Cyrillic_Pro", "Cyrl", "wide Cyrillic coverage"),
          ("GF_Greek_Core", "Grek", "modern Greek"),
          ("GF_Greek_Plus", "Grek", "adds to Greek Core (only the additions)"),
          ("GF_Greek_Pro", "Grek", "adds to Greek Plus (only the additions)"),
          ("GF_Arabic_Core", "Arab", "Arabic, Persian, Urdu"),
          ("GF_Arabic_Plus", "Arab", "more Arabic-script languages")]


def printable(codec, start=0x20):
    out = set()
    for b in range(start, 256):
        try:
            ch = bytes([b]).decode(codec)
        except UnicodeDecodeError:
            continue
        if ch.isprintable() or ch in " ­":
            out.add(ord(ch))
    return out


def nam(path):
    return {int(m.group(1), 16) for line in open(path, encoding="utf-8") if (m := re.match(r"0x([0-9A-Fa-f]+)", line))}


def read_existing():
    """The sets already in charsets.json, in either format (lists of integers, or hex-range strings)."""
    if not os.path.exists(TARGET):
        return {}
    with open(TARGET, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: set(v) if isinstance(v, list) else cs.decode(v) for k, v in raw.items() if not k.startswith("_")}


def main(gfsets):
    old = read_existing()
    sets, meta = {}, {}

    def add(name, cps, script, group, note=""):
        sets[name] = cps
        meta[name] = {"script": script, "group": group, "note": note}

    add("ASCII", printable("ascii", 0x20) & set(range(0x20, 0x7F)), "Latn", "ISO / ASCII", "printable ASCII")
    add("Latin 1 (ISO 8859-1)", {c for c in printable("latin-1") if c >= 0x20 and not 0x7F <= c < 0xA0}, "Latn", "ISO / ASCII",
        "Western European, the old ISO standard")
    for name, codec, script in WINDOWS:
        add(name, printable(codec), script, "Windows", f"printable characters of Windows code page {codec[2:]}")
    for n in range(1, 6):
        key = f"Adobe Latin {n}"
        if key not in old:
            raise SystemExit(f"{key} is read from the existing charsets.json; it is missing")
        add(key, old[key], "Latn", "Adobe", "adobe-type-tools Latin character sets, precomposed")
    for gf, script, note in GOOGLE:
        add(gf.replace("_", " ", 1).replace("_", " "), nam(os.path.join(gfsets, "data", "results", "nam", gf + ".nam")),
            script, "Google Fonts", note)
    if "Western European (cp1252)" in old:
        assert old["Western European (cp1252)"] == sets["Western European (cp1252)"], "cp1252 changed"
    out = {"_source": "ASCII and ISO 8859-1, Windows code pages (Python codecs); Adobe Latin 1–5 (adobe-type-tools, MIT); "
                      "Google Fonts glyphsets (googlefonts/glyphsets, Apache-2.0)",
           "_license": "see LICENSE-GLYPHSETS.txt for the Google Fonts sets",
           "_meta": meta}
    out.update({k: cs.encode(v) for k, v in sets.items()})
    with open(TARGET, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    lic = os.path.join(gfsets, "LICENSE")
    if os.path.exists(lic):
        import shutil
        shutil.copy(lic, os.path.join(HERE, "..", "core", "data", "LICENSE-GLYPHSETS.txt"))
    print(f"{len(sets)} sets, {os.path.getsize(TARGET) / 1024:.0f} KB → {TARGET}")


if __name__ == "__main__":
    main(sys.argv[1])
