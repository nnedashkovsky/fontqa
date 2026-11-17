"""Which languages a character set covers, from Unicode CLDR exemplar characters.

CLDR lists, for every language, the letters its everyday writing needs
(`exemplarCharacters`, the "main" set). A font supports a language when it has
all of them, upper and lower case; it is one step away when 1–3 letters are
missing. The data file `data/languages.json` is built by
`scripts/build_languages.py` from CLDR JSON (Unicode License v3, see
`data/LICENSE-CLDR.txt`), so nothing is downloaded at run time and the
browser reads the same file as the terminal.

Letters are stored compactly: one string of space-separated tokens, a token
being a unit (a letter, or a short sequence such as a base with a combining
mark), `U+AC00-D7A3` for a run of code points, and `\\uXXXX` escapes for
spaces, controls and combining marks.
"""

import json
import os
import unicodedata

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "languages.json")

ALMOST_MAX_MISSING = 3         # letters missing for "one step away"
ALMOST_MIN_SHARE = 0.7         # and at least this share of the language's letters present
ALMOST_MIN_SPEAKERS = 1_000_000  # languages smaller than this are not reported as findings

_DB = None


# ------------------------------------------------------------------ compact text <-> units

def _esc(ch):
    cp = ord(ch)
    if ch == "\\" or unicodedata.category(ch)[0] in "ZCM":
        return f"\\u{cp:04X}" if cp <= 0xFFFF else f"\\U{cp:08X}"
    return ch


def encode_units(units):
    """Units (strings) -> one compact string; runs of 4+ consecutive single code points become ranges."""
    out, i = [], 0
    units = list(units)
    while i < len(units):
        u = units[i]
        if len(u) == 1 and not unicodedata.category(u)[0] in "ZCM":
            j = i
            while j + 1 < len(units) and len(units[j + 1]) == 1 and ord(units[j + 1]) == ord(units[j]) + 1:
                j += 1
            if j - i >= 3:
                out.append(f"U+{ord(u):04X}-{ord(units[j]):04X}")
                i = j + 1
                continue
        out.append("".join(_esc(c) for c in u))
        i += 1
    return " ".join(out)


def _unesc(token):
    out, i = [], 0
    while i < len(token):
        c = token[i]
        if c == "\\" and i + 1 < len(token):
            if token[i + 1] == "u":
                out.append(chr(int(token[i + 2:i + 6], 16)))
                i += 6
                continue
            if token[i + 1] == "U":
                out.append(chr(int(token[i + 2:i + 10], 16)))
                i += 10
                continue
        out.append(c)
        i += 1
    return "".join(out)


def decode_units(text):
    units = []
    for token in text.split():
        if token.startswith("U+") and "-" in token:
            lo, hi = token[2:].split("-")
            units.extend(chr(c) for c in range(int(lo, 16), int(hi, 16) + 1))
        else:
            units.append(_unesc(token))
    return units


# ------------------------------------------------------------------ the database

def _letters(units):
    """Units -> unique (lower, upper-or-None) pairs; a sequence has no case partner."""
    seen, out = set(), []
    for u in units:
        if len(u) == 1:
            up = u.upper()
            pair = (u, up if len(up) == 1 and up != u else None)
        else:
            pair = (u, None)
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def database():
    """{"source", "scripts", "languages": [{tag, name, script, speakers, letters, aux}]}, read once."""
    global _DB
    if _DB is None:
        with open(DATA_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        langs = []
        for tag, d in sorted(raw["languages"].items()):
            letters = _letters(decode_units(d["main"]))
            langs.append({"tag": tag, "name": d["name"], "script": d["script"], "speakers": d["speakers"],
                          "letters": letters,
                          # every code point any letter needs: one set difference tells most languages apart
                          "cps": frozenset(ord(c) for lo, up in letters for form in (lo, up) if form for c in form)})
        _DB = {"source": raw["_source"], "scripts": raw["scripts"], "languages": langs}
    return _DB


# ------------------------------------------------------------------ coverage

_CACHE = {}


def coverage(cmap, compose=False):
    """`_coverage` with a memo: the fonts of a family mostly share one character set."""
    key = (frozenset(cmap), bool(compose))
    hit = _CACHE.get(key)
    if hit is None:
        if len(_CACHE) >= 64:
            _CACHE.pop(next(iter(_CACHE)))
        hit = _CACHE[key] = _coverage(key[0], key[1])
    return hit


def _coverage(cmap, compose):
    """Languages a code-point set supports, and those one step away.

    compose: the font positions combining marks (has a GPOS `mark` feature), so a letter that is
    not encoded as one glyph still counts when its base and its mark are.

    Returns {"supported": [lang], "almost": [{"lang": lang, "missing": [strings], "letters": n}]}.
    """
    cache = {}

    def has(cp):
        r = cache.get(cp)
        if r is None:
            r = cp in cmap
            if not r and compose:
                parts = unicodedata.normalize("NFD", chr(cp))
                r = len(parts) > 1 and all(ord(p) in cmap for p in parts)
            cache[cp] = r
        return r

    def ok(form):
        return all(has(ord(c)) for c in form)

    supported, almost = [], []
    for lang in database()["languages"]:
        gone = lang["cps"] - cmap
        if not gone:
            supported.append(lang)
            continue
        if not compose and len(gone) > 4 * ALMOST_MAX_MISSING:
            continue  # far too many missing for "one step away"; composing marks could still save letters, so not then
        lost = []  # forms of the missing letters, in order
        letters_missing = 0
        for lo, up in lang["letters"]:
            miss = [f for f in (lo, up) if f and not ok(f)]
            if miss:
                letters_missing += 1
                lost.extend(miss)
        total = len(lang["letters"])
        if not letters_missing:
            supported.append(lang)
        elif letters_missing <= ALMOST_MAX_MISSING and (total - letters_missing) / total >= ALMOST_MIN_SHARE:
            almost.append({"lang": lang, "missing": lost, "letters": letters_missing})
    return {"supported": supported, "almost": almost}
