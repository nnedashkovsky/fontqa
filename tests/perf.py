#!/usr/bin/env python3
"""How long the page takes to start and to check, measured in headless Chromium.

    python tests/perf.py [--json out.json] [--files 60]

Serves the built site and a generated delivery locally (the Pyodide and HarfBuzz CDNs are
the real ones, so the numbers include the network) and reports:

  cold start    a fresh browser profile: time until the engine says ready
  warm start    the same profile, page loaded again: HTTP cache warm
  first check   a 2-font delivery, Designer and then Engineer (the first Engineer run installs openpyxl)
  second check  the same again
  big delivery  N generated files, Engineer
  requests      what the page asked for: own files, CDNs, PyPI

Needs `pip install playwright && playwright install chromium`.
"""

import argparse
import functools
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import build_site  # noqa: E402
import fontkit as fk  # noqa: E402

RUN = """
async ([rels, level, attachments]) => {
  const files = await Promise.all(rels.map(async (rel) => ({ path: rel, buf: await (await fetch("/" + rel)).arrayBuffer() })));
  let t = performance.now();
  await window.checker.setTarget(files);
  const read = performance.now() - t;
  window.checker.state.busy = false;
  t = performance.now();
  const out = await window.checker.runInspection({ attachments, level });
  if (!out) throw new Error("no report");
  return { read_s: read / 1000, check_s: (performance.now() - t) / 1000, issues: out.issues.issues.length, kb: Math.round(out.html.length / 1024) };
}
"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def delivery(folder, n):
    fk.family(folder, name="Test Sans")
    fk.build(os.path.join(folder, "Desktop", "Broken-Regular.ttf"), family="Broken Sans With A Very Long Family Name",
             names={"version": "1.000"}, widths={0xA0: 400})
    small = sorted(os.path.relpath(os.path.join(r, f), folder) for r, _, fs in os.walk(folder) for f in fs)
    big = os.path.join(folder, "big")
    for i in range((n - 4) // 4 + 1):
        fk.family(big, name=f"Test Family {i:02d}")
    bigfiles = sorted(os.path.relpath(os.path.join(r, f), folder) for r, _, fs in os.walk(big) for f in fs)[:n]
    return small, bigfiles


def classify(url):
    host = url.split("/")[2] if "://" in url else ""
    if host.startswith("127.0.0.1"):
        return "own"
    if "jsdelivr" in host:
        return "cdn (jsdelivr)"
    if "pypi" in host or "pythonhosted" in host:
        return "pypi"
    return host or "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--files", type=int, default=60)
    ap.add_argument("--sw", action="store_true", help="let the page register its service worker (it does not on localhost) and also measure an offline start")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    site = tempfile.mkdtemp(prefix="fontqa-perf-")
    result = {}
    try:
        build_site.main(site)
        small, big = delivery(os.path.join(site, "fonts"), args.files)
        small = ["fonts/" + p for p in small if not p.startswith("big")]
        big = ["fonts/" + p for p in big]
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=site))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/web/"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            if args.sw:
                page.add_init_script("try{localStorage.setItem('fontqa:sw','1')}catch(e){}")
            seen = []
            page.on("request", lambda r: seen.append((time.time(), r.url)))

            def boot(label):
                seen.clear()
                t = time.time()
                page.goto(url)
                page.wait_for_function("document.body.innerText.includes('ready ·')", timeout=240_000)
                ms = page.evaluate("window.checker.state.env.boot_ms")
                result[label] = {"seconds_to_ready": round(time.time() - t, 2), "engine_boot_s": round(ms / 1000, 2),
                                 "requests": dict(Counter(classify(u) for _, u in seen))}

            boot("cold start")
            if args.sw:
                page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller || true")
                time.sleep(2)  # let the worker finish activating and cache what it has seen
            boot("warm start")
            if args.sw:
                ctx.set_offline(True)
                boot("offline start")
                ctx.set_offline(False)
            page.evaluate("localStorage.removeItem('fontqa:level')")  # no automatic run while measuring
            seen.clear()
            for label, level, files, att in (("first check, Designer, 2 fonts", "designer", small, False), ("first check, Engineer, 2 fonts", "engineer", small, False),
                                        ("second check, Engineer, 2 fonts", "engineer", small, False),
                                        ("check with attachments, Engineer, 2 fonts", "engineer", small, True),
                                        (f"big delivery, Engineer, {len(big)} files", "engineer", big, False)):
                t = time.time()
                r = page.evaluate(RUN, [files, level, att])
                r["seconds"] = round(time.time() - t, 2)
                r["read_s"], r["check_s"] = round(r["read_s"], 2), round(r["check_s"], 2)
                result[label] = r
            result["requests during the checks"] = dict(Counter(classify(u) for _, u in seen))
            browser.close()
        server.shutdown()
    finally:
        shutil.rmtree(site, ignore_errors=True)
    for k, v in result.items():
        print(f"{k:40} {v}")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=1)


if __name__ == "__main__":
    main()
