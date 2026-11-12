"""Terminal entry point: the reference run the browser is compared against.

    python3 -m core inventory <folder or files…> -o inventory.json
    python3 -m core shape     <folder or files…> -o shape.json
    python3 -m core fontbakery <files…> [--profile universal] -o fb.json
    python3 -m core hyperglot  <files…> [--marks] -o hg.json
    python3 -m core compare a.json b.json
    python3 -m core inspect <folder or files…> --out DIR [--fontbakery] [--font-json design/font.json]

Run from the repository root (the wrapper `check.sh` does that).
"""

import argparse
import json
import os
import sys

from . import inventory


def ots_verdicts(paths):
    """{relpath: 'ok' | message} from the ots module; None when it is not installed."""
    try:
        import ots
    except ImportError:
        return None
    import tempfile
    out = {}
    for p, rel in paths:
        res = ots.sanitize(p, os.devnull, capture_output=True)
        text = (res.stderr or b"").decode("utf-8", "replace").strip() or (res.stdout or b"").decode("utf-8", "replace").strip()
        if res.returncode and "WOFF 2.0" in text:
            # the CLI refuses WOFF2 that decompresses past 30 MB (large CJK fonts); Chrome
            # accepts them, so sanitize the decompressed tables instead of the container
            from fontTools.ttLib import TTFont
            with tempfile.NamedTemporaryFile(suffix=".ttf") as tmp:
                font = TTFont(p)
                font.flavor = None
                font.save(tmp.name)
                res = ots.sanitize(tmp.name, os.devnull, capture_output=True)
                text = (res.stderr or b"").decode("utf-8", "replace").strip()
        out[rel] = "ok" if res.returncode == 0 else (text.splitlines()[-1] if text else f"exit {res.returncode}")
    return out


def write_reports(result, out_dir, paths=None, refs=(), attachments=True):
    from .report_html import render as render_html
    from .report_xlsx import render as render_xlsx
    os.makedirs(out_dir, exist_ok=True)
    _dump(result, os.path.join(out_dir, "issues.json"))
    extra, names = "", []
    if attachments and paths:
        from . import attachments as att
        views = att.views_for(paths)
        up, it = att.default_refs(refs)
        pages = att.build(views, up, it, result["title"])
        pages["menus.html"] = att.menus_page(result)
        for name, page in pages.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write(page)
            names.append(name)
        extra = att.specimen_section(views)
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html(result, extra, names))
    with open(os.path.join(out_dir, "report.xlsx"), "wb") as fh:
        fh.write(render_xlsx(result))


def _dump(obj, path):
    text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)


def _sfnt_only(paths):
    return [(p, r) for p, r in paths if r.lower().endswith((".ttf", ".otf"))]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="core")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("inventory", "shape", "fontbakery", "hyperglot"):
        p = sub.add_parser(name)
        p.add_argument("inputs", nargs="+")
        p.add_argument("-o", "--output")
        if name == "fontbakery":
            p.add_argument("--profile", default="universal")
        if name == "hyperglot":
            p.add_argument("--marks", action="store_true")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("rules", help="check the rule cards against the code; --out writes the Rules page")
    p.add_argument("--out", help="HTML file for the Rules page")
    p = sub.add_parser("inspect")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--out", required=True, help="folder for issues.json, report.html, report.xlsx")
    p.add_argument("--profile", default="release")
    p.add_argument("--fontbakery", action="store_true", help="also run Font Bakery (universal)")
    p.add_argument("--font-json", help="design/font.json of the project, to check promo facts")
    p.add_argument("--no-ots", action="store_true")
    p.add_argument("--json-only", action="store_true")
    p.add_argument("--ref", action="append", default=[], help="your own reference font (repeatable)")
    p.add_argument("--no-attachments", action="store_true", help="skip glyph grids, GSUB listing and proofs")
    p.add_argument("--checks", help="comma-separated check-id prefixes to run only those, e.g. vf.,lineage.")
    args = ap.parse_args(argv)

    if args.cmd == "inspect":
        from .inspection import run
        paths = inventory.collect(args.inputs)
        if not paths:
            print("no font files found", file=sys.stderr)
            return 2
        tick = lambda n, total, rel: print(f"\r{n + 1}/{total} {rel[-70:]:<70}", end="", file=sys.stderr)
        ots_map = None if args.no_ots else ots_verdicts(paths)
        fb = None
        if args.fontbakery:
            from .probes import run_fontbakery
            fb = run_fontbakery([(p, r) for p, r in paths if r.lower().endswith((".ttf", ".otf"))])
        fj = None
        if args.font_json:
            with open(args.font_json, encoding="utf-8") as fh:
                fj = json.load(fh)
        only = [c.strip() for c in args.checks.split(",")] if args.checks else None
        result = run(paths, profile=args.profile, ots=ots_map, fontbakery=fb, font_json=fj, progress=tick, only=only)
        print(file=sys.stderr)
        if args.json_only:
            os.makedirs(args.out, exist_ok=True)
            _dump(result, os.path.join(args.out, "issues.json"))
        else:
            refs = [(os.path.splitext(os.path.basename(r))[0], os.path.abspath(r)) for r in args.ref]
            write_reports(result, args.out, paths, refs, attachments=not args.no_attachments)
        s = result["summary"]
        print(f"{s['issues']} issues ({s['by_action']}), {s['symptoms']} predicted symptoms, "
              f"{len(result['errors'])} check errors → {args.out}")
        for e in result["errors"]:
            print("  error:", e["check"], e["error"], file=sys.stderr)
        return 0

    if args.cmd == "rules":
        from . import rules
        from .checks import load_all
        registry = load_all()
        cards = rules.load()
        errors, notes = rules.validate(cards, registry)
        for n in notes:
            print("note:", n)
        for err in errors:
            print("error:", err, file=sys.stderr)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(rules.render_page(cards, registry))
            print(f"{len(cards)} cards, {len(registry)} checks → {args.out}")
        return 1 if errors else 0

    if args.cmd == "compare":
        with open(args.a) as fa, open(args.b) as fb:
            res = inventory.compare(json.load(fa), json.load(fb))
        _dump(res, None)
        return 0 if res["same"] else 1

    paths = inventory.collect(args.inputs)
    if not paths:
        print("no font files found", file=sys.stderr)
        return 2
    if args.cmd == "inventory":
        result = inventory.build(inventory.facts_for(paths))
    elif args.cmd == "shape":
        from .shaping import shape_files
        result = shape_files(_sfnt_only(paths))
    elif args.cmd == "fontbakery":
        from .probes import run_fontbakery
        result = run_fontbakery(paths, args.profile)
    else:
        from .probes import run_hyperglot
        result = run_hyperglot(paths, marks=args.marks)
    result["environment"] = inventory.environment()
    _dump(result, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
