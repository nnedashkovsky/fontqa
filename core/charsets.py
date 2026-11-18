"""Named character sets, and how much of each a font has.

The sets live in `data/charsets.json`, built by `scripts/build_charsets.py`:
ASCII and ISO 8859-1, the Windows code pages 1250–1258 (from Python's codecs),
Adobe Latin 1–5 (adobe-type-tools, MIT) and the Google Fonts glyphsets
(googlefonts/glyphsets, Apache-2.0). A set is a string of hex ranges:
"0020-007E 00A0-00FF 20AC".
"""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "charsets.json")
_DB = None


def encode(cps):
    """Code points -> 'AAAA-BBBB CCCC' ranges (runs of 2+ become a range)."""
    cps = sorted(set(cps))
    out, i = [], 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append(f"{cps[i]:04X}" if j == i else f"{cps[i]:04X}-{cps[j]:04X}")
        i = j + 1
    return " ".join(out)


def decode(text):
    out = set()
    for token in text.split():
        if "-" in token:
            lo, hi = token.split("-")
            out.update(range(int(lo, 16), int(hi, 16) + 1))
        else:
            out.add(int(token, 16))
    return out


def ranges(cps):
    """Sorted code points -> [[first, last], …] for issues.json."""
    return [[int(a, 16), int(b or a, 16)] for a, _, b in (t.partition("-") for t in encode(cps).split())]


def expand(rs):
    return [c for a, b in rs for c in range(a, b + 1)]


def database():
    """{"source", "sets": {name: frozenset}, "meta": {name: {"script", "group", "note"}}}, read once."""
    global _DB
    if _DB is None:
        with open(DATA_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        sets = {k: frozenset(decode(v)) for k, v in raw.items() if not k.startswith("_")}
        _DB = {"source": raw["_source"], "sets": sets, "meta": raw["_meta"]}
    return _DB


def sets():
    return database()["sets"]


def coverage(cmap, extra=None):
    """{name: {"have": n, "total": n, "missing": [code points]}} for every set, in file order.

    `extra` maps more names to code point sets (a project's own); they get script "" and group "Yours".
    """
    cmap = frozenset(cmap)
    out = {}
    for name, cps in {**sets(), **(extra or {})}.items():
        gone = sorted(cps - cmap)
        out[name] = {"have": len(cps) - len(gone), "total": len(cps), "missing": gone}
    return out
