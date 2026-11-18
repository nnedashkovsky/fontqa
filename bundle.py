"""The core and the rule cards as one JSON file, so the page loads them in one request.

`core.bundle.json` is {"hash", "core": {"core/<path>": text}, "rules": {"<name>.md": text}}. The hash
changes whenever any of those files does; the service worker names its cache after it. build_site.py
writes the file for the static site, serve.py answers it on the fly for the local page.
"""

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def make(root=HERE):
    core, rules = {}, {}
    base = os.path.join(root, "core")
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
        for n in sorted(names):
            if n.endswith(".py") or os.path.relpath(folder, base).startswith("data"):
                rel = os.path.relpath(os.path.join(folder, n), base).replace(os.sep, "/")
                with open(os.path.join(folder, n), encoding="utf-8") as fh:
                    core[rel] = fh.read()
    rdir = os.path.join(root, "rules")
    if os.path.isdir(rdir):
        for n in sorted(os.listdir(rdir)):
            if n.endswith(".md"):
                with open(os.path.join(rdir, n), encoding="utf-8") as fh:
                    rules[n] = fh.read()
    digest = hashlib.sha256()
    for group in (core, rules):
        for k, v in group.items():
            digest.update(k.encode() + b"\0" + v.encode() + b"\0")
    return {"hash": digest.hexdigest()[:12], "core": core, "rules": rules}


def dumps(root=HERE):
    return json.dumps(make(root), ensure_ascii=False, separators=(",", ":"))
