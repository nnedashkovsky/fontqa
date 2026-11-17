#!/usr/bin/env python3
"""The browser must report what the terminal reports, field for field.

Builds the static site, puts the clean test set next to it, runs the
inspection once in the terminal and once in headless Chromium (the page
exactly as GitHub Pages serves it, Pyodide included) at both levels, and
compares the two issues.json with the tool's own `compare`.

    python tests/browser_parity.py

Needs `pip install playwright` and `playwright install chromium`, and network
access for the Pyodide and HarfBuzz CDNs.
"""

import functools
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import build_site  # noqa: E402
import fontkit as fk  # noqa: E402
from core import inventory  # noqa: E402
from core.inspection import run  # noqa: E402
from test_checks import DIGITS_TF, FEA_CLEAN, W, add_legacy_kern, features_font  # noqa: E402

RUN_IN_PAGE = """
async ([rels, level, preset]) => {
  const files = await Promise.all(rels.map(async (rel) =>
    ({ path: rel, buf: await (await fetch("/" + rel)).arrayBuffer() })));
  await window.checker.setTarget(files);
  const out = await window.checker.runInspection({ attachments: false, level, preset });
  if (!out) throw new Error(document.querySelector("#insp-state").textContent);
  return JSON.stringify(out.issues);
}
"""


def clean_set(folder):
    fk.family(folder)
    fk.family(folder, name="Test Serif", ext=".otf")
    features_font(folder)
    fk.build(os.path.join(folder, "Web", "TestFeat-Regular.woff2"), family="Test Feat", chars=W + [0x301],
             widths={0x301: 0}, extra_glyphs=DIGITS_TF, fea=FEA_CLEAN, mutate=add_legacy_kern,
             flavor="woff2", post_names=False)
    fk.variable(folder)
    # one broken font, so that findings, symptoms and menus are compared too, not only their absence
    fk.build(os.path.join(folder, "Desktop", "Broken-Regular.ttf"), family="Broken Sans With A Very Long Family Name",
             names={"version": "1.000"}, widths={0xA0: 400}, os2={"fsSelection": 0x40})


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(folder):
    handler = functools.partial(Quiet, directory=folder)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    from playwright.sync_api import sync_playwright
    site = tempfile.mkdtemp(prefix="fontqa-site-")
    failed = False
    try:
        build_site.main(site)
        clean_set(os.path.join(site, "fonts"))
        paths = inventory.collect([os.path.join(site, "fonts")])
        rels = [rel for _, rel in paths]
        server = serve(site)
        url = f"http://127.0.0.1:{server.server_address[1]}/web/"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.on("pageerror", lambda err: print("page error:", err))
            page.goto(url)
            page.wait_for_function("document.body.innerText.includes('ready ·')", timeout=180_000)
            # (level, preset): full runs at both levels, and the selections that change what runs
            for level, preset in (("designer", None), ("engineer", None), ("engineer", "differences"), ("designer", "glyphs")):
                in_browser = json.loads(page.evaluate(RUN_IN_PAGE, [rels, level, preset]))
                ots = {rel: "ok" for rel in rels}  # the browser loaded every font, which is its OTS verdict
                in_terminal = json.loads(json.dumps(run(paths, ots=ots, level=level, preset=preset)))
                level = f"{level} / {preset or 'all'}"
                res = inventory.compare(in_terminal, in_browser)
                n = len(in_browser["issues"])
                if res["same"]:
                    print(f"{level}: same as terminal ({len(in_browser['checks'])} checks, {n} issues)")
                else:
                    failed = True
                    print(f"{level}: {len(res['diffs'])} differences")
                    for d in res["diffs"][:20]:
                        print("  ", d["at"], "| terminal:", d["a"], "| browser:", d["b"])
            browser.close()
        server.shutdown()
    finally:
        shutil.rmtree(site, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
