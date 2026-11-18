#!/usr/bin/env python3
"""Build the static site for GitHub Pages into _site/.

The local server (serve.py) answers <folder>/__list.json on the fly; a static
host cannot, so the list for core/ is written as a file here. The page itself
is unchanged: open _site/web/.
"""

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Pure-Python wheels the page installs in the browser, served from the site itself: no request to PyPI.
# openpyxl writes the xlsx report; munkres is for the variable-font master check. Versions match requirements.txt.
WHEELS = {"openpyxl": ["et_xmlfile==2.0.0", "openpyxl==3.1.5"], "munkres": ["munkres==1.1.4"]}
WHEEL_CACHE = os.path.join(HERE, ".wheels")


def fetch_wheels(dest):
    """Download the wheels once (kept in .wheels/) and copy them next to the site; returns {package: [file names]}."""
    os.makedirs(WHEEL_CACHE, exist_ok=True)
    os.makedirs(dest, exist_ok=True)
    out = {}
    for package, specs in WHEELS.items():
        names = []
        for spec in specs:
            stem = spec.split("==")[0].lower().replace("-", "_")
            have = [f for f in os.listdir(WHEEL_CACHE) if f.lower().startswith(stem + "-") and f.endswith(".whl")]
            if not have:
                res = subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
                                      "-q", "-d", WHEEL_CACHE, spec], capture_output=True, text=True)
                have = [f for f in os.listdir(WHEEL_CACHE) if f.lower().startswith(stem + "-") and f.endswith(".whl")]
                if res.returncode or not have:
                    print(f"warning: could not fetch {spec}; the page will install {package} from PyPI", file=sys.stderr)
                    names = []
                    break
            shutil.copy(os.path.join(WHEEL_CACHE, have[0]), os.path.join(dest, have[0]))
            names.append(have[0])
        if names:
            out[package] = names
    return out


def main(out=os.path.join(HERE, "_site")):
    shutil.rmtree(out, ignore_errors=True)
    skip = shutil.ignore_patterns("__pycache__", "*.pyc", ".*", "sw.js")
    for d in ("web", "core"):
        shutil.copytree(os.path.join(HERE, d), os.path.join(out, d), ignore=skip)
    core = os.path.join(out, "core")
    files = sorted(os.path.relpath(os.path.join(r, n), core).replace(os.sep, "/")
                   for r, _, names in os.walk(core) for n in names)
    with open(os.path.join(core, "__list.json"), "w") as f:
        json.dump({"base": "core", "files": files}, f)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=web/">'
                '<title>Redirect</title><a href="web/">Open Font QA</a>\n')
    sys.path.insert(0, HERE)
    from core import rules
    from core.checks import load_all
    registry = load_all()
    cards = rules.load()
    errors, _ = rules.validate(cards, registry)
    if errors:
        sys.exit("rule cards disagree with the code:\n  " + "\n  ".join(errors))
    os.makedirs(os.path.join(out, "rules"))
    md = sorted(n for n in os.listdir(rules.RULES_DIR) if n.endswith(".md"))
    for n in md:
        shutil.copy(os.path.join(rules.RULES_DIR, n), os.path.join(out, "rules", n))
    with open(os.path.join(out, "rules", "__list.json"), "w") as f:
        json.dump({"base": "rules", "files": md}, f)
    with open(os.path.join(out, "rules", "index.html"), "w", encoding="utf-8") as f:
        f.write(rules.render_page(cards, registry))
    import bundle
    data = bundle.make(HERE)
    with open(os.path.join(out, "core.bundle.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, "wheels.json"), "w") as f:
        json.dump(fetch_wheels(os.path.join(out, "wheels")), f)
    with open(os.path.join(HERE, "web", "sw.js"), encoding="utf-8") as f:
        sw = f.read().replace("__VERSION__", data["hash"])
    with open(os.path.join(out, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw)
    open(os.path.join(out, ".nojekyll"), "w").close()
    print(f"{len(files)} core files, {len(md)} rule cards, bundle {data['hash']} → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
