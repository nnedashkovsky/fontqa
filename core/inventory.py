"""Inventory of a delivery: which files, which families, which lineages.

This is the first page of every report (RT opens the same way: "100 files: 24
static weights x App / Desktop / Web woff / woff2, plus 4 VF"). It is not a
check yet; it only states what was received, with hashes, so the report can
name its inputs exactly. RT once compared a package against a stale build
config and nothing in their report showed it; hashes here make that visible.

Paths are relative to the parent of the folder that was given (or dropped), so
the terminal and the browser name the same file the same way and their outputs
can be compared key by key.
"""

import hashlib
import os
import sys
from collections import Counter, defaultdict

import fontTools

from . import VERSION
from .facts import FONT_EXTENSIONS, file_facts

LINEAGES = {"app": "App", "desktop": "Desktop", "web": "Web"}


def environment():
    return {
        "tool": "Font QA",
        "core": VERSION,
        "fontTools": fontTools.version,
        "python": sys.version.split()[0],
        "env": "browser" if sys.platform == "emscripten" else "terminal",
    }


def collect(inputs):
    """(abs path, relpath) for every font under the given files and folders."""
    found = []
    for item in inputs:
        item = os.path.abspath(item)
        if os.path.isdir(item):
            base = os.path.dirname(item)
            for root, dirs, files in os.walk(item):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                for fn in sorted(files):
                    if fn.lower().endswith(FONT_EXTENSIONS) and not fn.startswith("."):
                        p = os.path.join(root, fn)
                        found.append((p, os.path.relpath(p, base).replace(os.sep, "/")))
        elif item.lower().endswith(FONT_EXTENSIONS):
            found.append((item, os.path.basename(item)))
    return sorted(found, key=lambda t: t[1])


def lineage(relpath, fmt):
    """App / Desktop / Web from the folder names; web formats imply Web."""
    for part in relpath.lower().split("/")[:-1]:
        for token, name in LINEAGES.items():
            if part == token or part.startswith(token + " ") or part.endswith(" " + token):
                return name
    if fmt in ("WOFF", "WOFF2"):
        return "Web"
    return None


def facts_for(paths, cached=None, progress=None):
    """Facts for (abs, rel) paths; `cached` maps sha256 -> facts from an earlier run."""
    out = []
    for n, (abspath, relpath) in enumerate(paths):
        if progress:
            progress(n, len(paths), relpath)
        with open(abspath, "rb") as fh:
            data = fh.read()
        f = None
        if cached:
            hit = cached.get(hashlib.sha256(data).hexdigest())
            if hit:
                f = dict(hit, path=relpath)
        out.append(f or file_facts(abspath, relpath, data))
    return out


def build(facts, role="target", references=None):
    """Inventory from per-file facts. `references` are inventoried separately."""
    files = sorted(facts, key=lambda f: f["path"])
    for f in files:
        f["lineage"] = lineage(f["path"], f.get("format"))
    inv = {
        "environment": environment(),
        "role": role,
        "files": files,
        "families": _families(files),
        "summary": _summary(files),
    }
    if references is not None:
        inv["references"] = build(references, role="reference")
    return inv


def _style_key(f):
    st = f.get("style", {})
    var = bool(f.get("variation"))
    return (st.get("subfamily") or "?", var)


def _families(files):
    fams = defaultdict(list)
    for f in files:
        if "error" not in f:
            fams[f["style"]["family"] or "?"].append(f)
    out = []
    for family in sorted(fams):
        members = fams[family]
        styles = defaultdict(list)
        for f in members:
            styles[_style_key(f)].append(f)
        def order(kv):
            st = kv[1][0]["style"]
            return (kv[0][1], st["weight_class"] or 0, "ITALIC" in (st["fs_selection"] or []), kv[0][0])

        style_rows = []
        for (sub, var), fs in sorted(styles.items(), key=order):
            st = fs[0]["style"]
            dupes = Counter((x["lineage"], x["format"]) for x in fs)
            style_rows.append({
                "subfamily": sub,
                "variable": var,
                "weight_class": st["weight_class"],
                "italic": "ITALIC" in (st["fs_selection"] or []),
                "files": [{"path": x["path"], "format": x["format"], "lineage": x["lineage"]} for x in fs],
                "duplicates": sorted(f"{k[0] or '—'}/{k[1]}" for k, n in dupes.items() if n > 1),
            })
        by_format = defaultdict(set)
        for f in members:
            by_format[f["format"]].add((f["glyphs"]["count"], f["glyphs"]["cmap"]))
        out.append({
            "family": family,
            "styles": style_rows,
            "formats": dict(sorted(Counter(f["format"] for f in members).items())),
            "lineages": dict(sorted(Counter(f["lineage"] or "—" for f in members).items())),
            "glyph_sets": {fmt: [list(t) for t in sorted(v)] for fmt, v in sorted(by_format.items())},
        })
    return out


def _summary(files):
    ok = [f for f in files if "error" not in f]
    return {
        "files": len(files),
        "fonts": len(ok),
        "errors": len(files) - len(ok),
        "bytes": sum(f["size"] for f in files),
        "formats": dict(sorted(Counter(f["format"] or "?" for f in files).items())),
        "lineages": dict(sorted(Counter(f["lineage"] or "—" for f in files).items())),
        "families": len({f["style"]["family"] for f in ok}),
        "variable": sum(1 for f in ok if f.get("variation")),
    }


def compare(a, b, ignore=("environment",)):
    """Key-by-key difference of two JSON results (inventory, probe, shaping).

    Lists of dicts that carry a "path" are matched by path, so one missing file
    does not shift every later comparison.
    """
    diffs = []

    def walk(x, y, where):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if not where and k in ignore:
                    continue
                if k not in x:
                    diffs.append({"at": f"{where}.{k}".lstrip("."), "a": "(missing)", "b": _short(y[k])})
                elif k not in y:
                    diffs.append({"at": f"{where}.{k}".lstrip("."), "a": _short(x[k]), "b": "(missing)"})
                else:
                    walk(x[k], y[k], f"{where}.{k}")
        elif (isinstance(x, list) and isinstance(y, list) and x and y
              and all(isinstance(i, dict) and "path" in i for i in x + y)):
            walk({i["path"]: i for i in x}, {i["path"]: i for i in y}, where)
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (p, q) in enumerate(zip(x, y)):
                walk(p, q, f"{where}[{i}]")
        elif x != y:
            diffs.append({"at": where.lstrip("."), "a": _short(x), "b": _short(y)})

    walk(a, b, "")
    return {"same": not diffs, "differences": len(diffs), "diffs": diffs[:500]}


def _short(v):
    s = repr(v)
    return v if len(s) <= 160 else s[:157] + "..."
