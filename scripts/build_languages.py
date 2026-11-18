#!/usr/bin/env python3
"""Build core/data/languages.json from Unicode CLDR JSON.

    git clone --depth 1 --branch 49.0.0 --filter=blob:none --sparse https://github.com/unicode-org/cldr-json.git cldr
    (cd cldr && git sparse-checkout set --skip-checks cldr-json/cldr-misc-full/main cldr-json/cldr-core/supplemental \
        cldr-json/cldr-localenames-full/main/en)
    python scripts/build_languages.py cldr/cldr-json

What is taken, per language tag (a language, or a language with a script, e.g. sr-Latn):
  main letters   cldr-misc-full/main/<tag>/characters.json  exemplarCharacters
  speakers       cldr-core/supplemental/territoryInfo.json  population × share, summed over territories
  names          cldr-localenames-full/main/en              languages and scripts
Languages with fewer than MIN_SPEAKERS speakers are left out, to keep the file small.
The CLDR data is under the Unicode License v3; its text is copied to core/data/LICENSE-CLDR.txt.
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from core.languages import encode_units  # noqa: E402

MIN_SPEAKERS = 100_000
REGION_MIN_SPEAKERS = 100_000  # a continent counts for a language with this many speakers in one territory of it
CONTINENTS = {"150": "EU", "142": "AS", "019": "AM", "002": "AF", "009": "OC"}


def parse_unicode_set(text):
    """Units of a CLDR UnicodeSet such as '[a ą b {ab} \\u0301 x-z]' (the subset exemplars use)."""
    s = text.strip()
    assert s[0] == "[" and s[-1] == "]", text[:40]
    s = s[1:-1]
    units, i = [], 0

    def char():
        nonlocal i
        c = s[i]
        if c == "\\":
            n = s[i + 1]
            if n == "u":
                i += 6
                return chr(int(s[i - 4:i], 16))
            if n == "U":
                i += 10
                return chr(int(s[i - 8:i], 16))
            i += 2
            return n
        i += 1
        return c

    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c == "{":
            j = s.index("}", i)
            inner = s[i + 1:j]
            k, seq = 0, []
            while k < len(inner):
                if inner[k] == "\\" and inner[k + 1] in "uU":
                    n = 4 if inner[k + 1] == "u" else 8
                    seq.append(chr(int(inner[k + 2:k + 2 + n], 16)))
                    k += 2 + n
                else:
                    seq.append(inner[k])
                    k += 1
            units.append("".join(seq))
            i = j + 1
        else:
            a = char()
            if i + 1 < len(s) and s[i] == "-" and s[i + 1] != "]":
                i += 1
                b = char()
                units.extend(chr(x) for x in range(ord(a), ord(b) + 1))
            else:
                units.append(a)
    return units


def main(root):
    def load(*parts):
        with open(os.path.join(root, *parts), encoding="utf-8") as fh:
            return json.load(fh)

    version = load("cldr-core", "package.json")["version"]
    contain = load("cldr-core", "supplemental", "territoryContainment.json")["supplemental"]["territoryContainment"]
    continent_of = {}

    def walk(code, continent):
        for child in contain.get(code, {}).get("_contains", []):
            continent_of.setdefault(child, continent)
            walk(child, continent)

    for code, name in CONTINENTS.items():
        walk(code, name)
    people, where = {}, {}
    for terr, d in load("cldr-core", "supplemental", "territoryInfo.json")["supplemental"]["territoryInfo"].items():
        pop = float(d["_population"])
        for key, v in d.get("languagePopulation", {}).items():
            n = pop * float(v["_populationPercent"]) / 100
            people[key] = people.get(key, 0) + n
            if n >= REGION_MIN_SPEAKERS and terr in continent_of:
                where.setdefault(key, set()).add(continent_of[terr])
    likely = load("cldr-core", "supplemental", "likelySubtags.json")["supplemental"]["likelySubtags"]
    names = load("cldr-localenames-full", "main", "en", "languages.json")["main"]["en"]["localeDisplayNames"]["languages"]
    scripts = load("cldr-localenames-full", "main", "en", "scripts.json")["main"]["en"]["localeDisplayNames"]["scripts"]
    out, used_scripts = {}, {}
    for tag in sorted(os.listdir(os.path.join(root, "cldr-misc-full", "main"))):
        parts = tag.split("-")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) != 4):
            continue  # a territory variant (en-GB): the language is already there
        lang = parts[0]
        script = parts[1] if len(parts) == 2 else likely.get(lang, "und-Zzzz").split("-")[1]
        default_script = likely.get(lang, "und-Zzzz").split("-")[1]
        n = people.get(f"{lang}_{script}")
        if n is None:
            n = people.get(lang, 0) if script == default_script else 0
        if n < MIN_SPEAKERS:
            continue
        chars = load("cldr-misc-full", "main", tag, "characters.json")["main"][tag]["characters"]
        main_set = chars.get("exemplarCharacters")
        if not main_set:
            continue
        name = names.get(lang, lang)
        if len(parts) == 2:
            name += f" ({scripts.get(script, script)})"
        regions = where.get(f"{lang}_{script}") or (where.get(lang) if script == default_script else None) or set()
        out[tag] = {"name": name, "script": script, "speakers": int(n), "regions": sorted(regions),
                    "main": encode_units(parse_unicode_set(main_set))}
        used_scripts[script] = scripts.get(script, script)
    data = {"_source": f"Unicode CLDR {version} (cldr-json): exemplar characters, territory population, English names",
            "_license": "Unicode License v3, see LICENSE-CLDR.txt", "scripts": dict(sorted(used_scripts.items())),
            "languages": out}
    target = os.path.join(HERE, "..", "core", "data", "languages.json")
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    shutil.copy(os.path.join(root, "..", "LICENSE"), os.path.join(HERE, "..", "core", "data", "LICENSE-CLDR.txt"))
    print(f"{len(out)} languages, {os.path.getsize(target) / 1024:.0f} KB → {target}")


if __name__ == "__main__":
    main(sys.argv[1])
