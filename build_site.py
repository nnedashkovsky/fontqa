#!/usr/bin/env python3
"""Build the static site for GitHub Pages into _site/.

The local server (serve.py) answers <folder>/__list.json on the fly; a static
host cannot, so the list for core/ is written as a file here. The page itself
is unchanged: open _site/web/.
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(out=os.path.join(HERE, "_site")):
    shutil.rmtree(out, ignore_errors=True)
    skip = shutil.ignore_patterns("__pycache__", "*.pyc", ".*")
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
    open(os.path.join(out, ".nojekyll"), "w").close()
    print(f"{out}: {len(files)} core files")


if __name__ == "__main__":
    main(*sys.argv[1:])
