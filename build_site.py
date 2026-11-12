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
    open(os.path.join(out, ".nojekyll"), "w").close()
    print(f"{out}: {len(files)} core files")


if __name__ == "__main__":
    main(*sys.argv[1:])
