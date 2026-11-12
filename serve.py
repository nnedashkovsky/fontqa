"""Local server for the Font QA page. Fonts never leave this machine.

Serves this folder at http://127.0.0.1:<port>/ (the page is /web/), the
reference fonts at /refs/, and any extra folders given with --mount at
/mnt/<name>/ (handy for loading a delivery without dragging it in, and for the
terminal reference JSON). Every folder answers <folder>/__list.json with its
files, so the page can fetch a whole tree. Binds to 127.0.0.1 only and sends
no-cache, so edits to the Python core show up on reload.
"""

import argparse
import functools
import http.server
import json
import mimetypes
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO_REFS = os.path.normpath(os.path.join(HERE, "..", "..", "CHECKER", "PT-EXPERT_FONTS"))
REFS = os.environ.get("FONTQA_REFS") or STUDIO_REFS  # optional folder of reference fonts

mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/otf", ".otf")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("text/x-python", ".py")


class Handler(http.server.SimpleHTTPRequestHandler):
    mounts = {}

    def translate_path(self, path):
        path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        for prefix, root in self.mounts.items():
            if path == prefix.rstrip("/") or path.startswith(prefix):
                rest = path[len(prefix):].lstrip("/")
                full = os.path.normpath(os.path.join(root, rest))
                return full if full.startswith(root) else root
        return super().translate_path(path)

    def do_GET(self):
        if self.path.split("?")[0] in ("/rules", "/rules/", "/rules/index.html"):
            # the Rules page is built from rules/*.md on every request, so edits show on reload
            sys.path.insert(0, HERE)
            from core import rules
            from core.checks import load_all
            body = rules.render_page(rules.load(), load_all()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.split("?")[0].endswith("/__list.json"):
            folder = self.translate_path(self.path.split("?")[0][: -len("__list.json")])
            if not os.path.isdir(folder):
                return self.send_error(404)
            files = []
            for root, dirs, names in os.walk(folder):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
                files += [os.path.relpath(os.path.join(root, n), folder).replace(os.sep, "/")
                          for n in sorted(names) if not n.startswith(".")]
            body = json.dumps({"base": os.path.basename(folder.rstrip(os.sep)), "files": files}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "--verbose" in sys.argv:
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Serve the Font QA page locally.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--mount", action="append", default=[], metavar="NAME=DIR",
                    help="also serve DIR at /mnt/NAME/")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    mounts = {"/refs/": REFS}
    for m in args.mount:
        name, _, folder = m.partition("=")
        mounts[f"/mnt/{name}/"] = os.path.abspath(os.path.expanduser(folder))
    Handler.mounts = mounts

    handler = functools.partial(Handler, directory=HERE)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Font QA: http://127.0.0.1:{args.port}/web/")
    for prefix, root in mounts.items():
        print(f"  {prefix:<14} {root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
