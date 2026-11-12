/* Font QA worker: the Python core under Pyodide, off the main thread.

   The page posts {id, cmd, ...}; the worker answers {id, ok, result|error} and
   streams {type:"progress"} while it works. Fonts are written into Pyodide's
   in-memory file system under /in/<role>/<path>, so the Python core sees the
   same relative paths the terminal run sees. Facts are cached in IndexedDB by
   sha256 + core version: a second look at the same delivery skips parsing.

   harfbuzzjs is loaded here too and exposed as self.hb; core/hbshim.py turns
   it into `uharfbuzz` for Python. */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
const HBJS = "https://cdn.jsdelivr.net/npm/harfbuzzjs@0.4.7/";
importScripts(PYODIDE + "pyodide.js", HBJS + "hb.js", HBJS + "hbjs.js");

let py = null;
let env = null;

const post = (msg) => self.postMessage(msg);
const status = (text) => post({ type: "status", text });

async function boot() {
  const t0 = performance.now();
  status("loading Pyodide");
  py = await loadPyodide({ indexURL: PYODIDE });
  status("loading fontTools");
  await py.loadPackage(["fonttools", "brotli", "micropip"]);
  status("loading HarfBuzz");
  self.hb = hbjs(await createHarfBuzz({ locateFile: (f) => HBJS + f }));
  // glyph id, cluster, x advance, x offset, y offset per glyph, flat: Python reads it as one buffer
  // instead of converting thousands of small objects (core/hbshim.py)
  self.hbFlat = (buffer) => {
    const j = buffer.json();
    const out = new Int32Array(j.length * 6);
    j.forEach((g, i) => out.set([g.g, g.cl, g.ax, g.ay, g.dx, g.dy], i * 6));
    return out;
  };
  status("loading the checker core");
  const list = await (await fetch("../core/__list.json", { cache: "no-store" })).json();
  py.FS.mkdirTree("/app/core");
  // fetched in parallel: one by one, the round trips of a static host add up to tens of seconds
  const coreFiles = list.files.filter((f) => f.endsWith(".py") || f.startsWith("data/"));
  const texts = await Promise.all(coreFiles.map(async (f) => (await fetch("../core/" + f, { cache: "no-cache" })).text()));
  coreFiles.forEach((f, i) => {
    py.FS.mkdirTree(("/app/core/" + f).split("/").slice(0, -1).join("/"));
    py.FS.writeFile("/app/core/" + f, texts[i]);
  });
  // rule cards: the report quotes "why it matters" and "how it is checked" from them
  try {
    const rl = await (await fetch("../rules/__list.json", { cache: "no-store" })).json();
    py.FS.mkdirTree("/app/rules");
    const cards = rl.files.filter((f) => f.endsWith(".md") && !f.includes("/"));
    const md = await Promise.all(cards.map(async (f) => (await fetch("../rules/" + f, { cache: "no-cache" })).text()));
    cards.forEach((f, i) => py.FS.writeFile("/app/rules/" + f, md[i]));
  } catch (err) { /* no cards: the report falls back to the short texts in the code */ }
  py.runPython(`import sys\nif "/app" not in sys.path: sys.path.insert(0, "/app")`);
  env = JSON.parse(py.runPython(`import json\nfrom core.inventory import environment\njson.dumps(environment())`));
  env.levels = JSON.parse(py.runPython(`import json\nfrom core import levels\njson.dumps({"css": levels.CSS, "panel": levels.panel()})`));
  env.harfbuzz = self.hb.version_string();
  env.pyodide = py.version;
  env.boot_ms = Math.round(performance.now() - t0);
  post({ type: "ready", env });
}

/* ---------- facts cache (IndexedDB) ---------- */

function idb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("fontqa", 2);
    req.onupgradeneeded = () => {
      for (const s of ["facts", "blobs"]) {
        if (!req.result.objectStoreNames.contains(s)) req.result.createObjectStore(s);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function cacheGet(keys, storeName = "facts") {
  try {
    const db = await idb();
    const store = db.transaction(storeName).objectStore(storeName);
    const out = {};
    await Promise.all(keys.map((k) => new Promise((res) => {
      const r = store.get(k);
      r.onsuccess = () => { if (r.result) out[k] = r.result; res(); };
      r.onerror = () => res();
    })));
    return out;
  } catch (e) { return {}; }
}

async function cachePut(entries, storeName = "facts") {
  try {
    const db = await idb();
    const tx = db.transaction(storeName, "readwrite");
    for (const [k, v] of entries) tx.objectStore(storeName).put(v, k);
    await new Promise((res) => { tx.oncomplete = res; tx.onerror = res; });
  } catch (e) { /* cache is a convenience; the run never depends on it */ }
}

async function sha256(buf) {
  const d = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* ---------- commands ---------- */

function writeFiles(role, files) {
  for (const f of files) {
    const full = `/in/${role}/${f.path}`;
    py.FS.mkdirTree(full.split("/").slice(0, -1).join("/"));
    py.FS.writeFile(full, new Uint8Array(f.buf));
  }
}

async function runPy(code, args) {
  py.globals.set("ARGS", JSON.stringify(args || {}));
  py.globals.set("progress_js", (n, total, path) => post({ type: "progress", n, total, path }));
  const out = await py.runPythonAsync(code);
  return JSON.parse(out);
}

const commands = {
  async inventory({ role, files }) {
    writeFiles(role, files);
    const shas = await Promise.all(files.map((f) => sha256(f.buf)));
    const keys = shas.map((s) => `${env.core}:${s}`);
    const hits = await cacheGet(keys);
    const cached = {};
    shas.forEach((s, i) => { if (hits[keys[i]]) cached[s] = hits[keys[i]]; });
    const inv = await runPy(`
import json
from core import inventory
a = json.loads(ARGS)
paths = [(f"/in/{a['role']}/{p}", p) for p in a["paths"]]
facts = inventory.facts_for(paths, a["cached"], progress=lambda n, t, p: progress_js(n, t, p))
json.dumps(inventory.build(facts, role=a["role"]), ensure_ascii=False, sort_keys=True)
`, { role, paths: files.map((f) => f.path), cached });
    const fresh = inv.files.filter((f) => !f.error && !cached[f.sha256]);
    await cachePut(fresh.map((f) => {
      const { path, lineage, ...rest } = f;
      return [`${env.core}:${f.sha256}`, rest];
    }));
    inv.cache = { hits: Object.keys(cached).length, stored: fresh.length };
    return inv;
  },

  async shape({ role, paths }) {
    return runPy(`
import json
from core import hbshim
hbshim.install()
from core.inventory import environment
from core.shaping import shape_files
a = json.loads(ARGS)
r = shape_files([(f"/in/{a['role']}/{p}", p) for p in a["paths"]])
r["environment"] = environment()
json.dumps(r, ensure_ascii=False, sort_keys=True)
`, { role, paths });
  },

  async probe({ tool, role, paths, marks }) {
    status(`preparing ${tool}`);
    const t0 = performance.now();
    // Hyperglot pickles its parsed language database; keep it between visits
    const HG_CACHE = "/tmp/.hyperglot-cache", HG_KEY = "hyperglot-0.8.1";
    if (tool === "hyperglot") {
      const hit = (await cacheGet([HG_KEY], "blobs"))[HG_KEY];
      if (hit) { py.FS.mkdirTree("/tmp"); py.FS.writeFile(HG_CACHE, new Uint8Array(hit)); }
    }
    py.globals.set("status_js", (line) => status(`${tool}: ${line}`));
    const setup = await runPy(`
import json
from core import browser
json.dumps(await browser.prepare(json.loads(ARGS)["tool"], report=status_js))
`, { tool });
    if (!setup.ok) return { setup, result: null };
    status(`running ${tool}`);
    const result = await runPy(`
import json, os
from core import probes
from core.inventory import environment
a = json.loads(ARGS)
paths = [(f"/in/{a['role']}/{p}", os.path.basename(p)) for p in a["paths"]]
if a["tool"] == "fontbakery":
    r = probes.run_fontbakery(paths)
else:
    r = probes.run_hyperglot(paths, marks=a.get("marks", False))
r["environment"] = environment()
json.dumps(r, ensure_ascii=False, sort_keys=True)
`, { tool, role, paths, marks: !!marks });
    if (tool === "hyperglot") {
      // the pickle fills up language by language during the run, so save it after
      try { await cachePut([[HG_KEY, py.FS.readFile(HG_CACHE).slice().buffer]], "blobs"); } catch (e) { /* no cache written */ }
    }
    setup.ms = Math.round(performance.now() - t0);
    return { setup, result };
  },

  async inspect({ role, paths, facts, ots, fontbakery, fontJson, refs, attachments, profile, level }) {
    const t0 = performance.now();
    let fb = null;
    if (fontbakery) {
      status("preparing Font Bakery");
      py.globals.set("status_js", (line) => status(`fontbakery: ${line}`));
      const setup = await runPy(`
import json
from core import browser
json.dumps(await browser.prepare("fontbakery", report=status_js))
`, {});
      if (setup.ok) {
        status("running Font Bakery");
        fb = await runPy(`
import json
from core import probes
a = json.loads(ARGS)
json.dumps(probes.run_fontbakery([(f"/in/{a['role']}/{p}", p) for p in a["paths"] if p.lower().endswith((".ttf", ".otf"))]))
`, { role, paths });
      }
    }
    status("installing openpyxl and munkres");
    await runPy(`
import json, micropip
try:
    import openpyxl
except ImportError:
    await micropip.install("openpyxl")
try:  # varLib.interpolatable matches contours with munkres (or scipy) — pure Python, small
    import munkres
except ImportError:
    await micropip.install("munkres")
json.dumps(True)
`, {});
    status("inspecting");
    const out = await runPy(`
import base64, json
from core import hbshim
hbshim.install()  # vf.vs_static shapes text through the uharfbuzz API
from core.inspection import run
from core.report_html import render as render_html
from core.report_xlsx import render as render_xlsx
a = json.loads(ARGS)
facts = [dict(f) for f in a["facts"]] if a["facts"] else None
paths = [(f"/in/{a['role']}/{p}", p) for p in a["paths"]]
prof = None
if a["profile"]:  # window.checker.runInspection({profile: true}) — where the browser spends its time
    import cProfile
    prof = cProfile.Profile()
    prof.enable()
r = run(paths, ots=a["ots"], fontbakery=a["fb"],
        font_json=a["fontJson"], facts=facts, progress=lambda n, t, p: progress_js(n, t, p), level=a["level"])
pages, extra = {}, ""
if a["attachments"]:
    from core import attachments as att
    att.REF_DIR = "/in/reference/PT-EXPERT_FONTS"
    views = att.views_for(paths, facts)
    up, it = att.default_refs([(p.split("/")[-1].rsplit(".", 1)[0], f"/in/reference/{p}") for p in a["refs"]])
    pages = att.build(views, up, it, r["title"])
    if r.get("menus"):
        pages["menus.html"] = att.menus_page(r)
    extra = att.specimen_section(views)
profile = ""
if prof:
    import io, pstats
    prof.disable()
    buf = io.StringIO()
    pstats.Stats(prof, stream=buf).sort_stats("cumulative").print_stats(60)
    buf.write(chr(10) + "--- by own time" + chr(10))  # no backslashes inside the JS template
    pstats.Stats(prof, stream=buf).sort_stats("tottime").print_stats(40)
    profile = buf.getvalue()
json.dumps({"issues": r, "profile": profile, "html": render_html(r, extra, list(pages)), "xlsx": base64.b64encode(render_xlsx(r)).decode(),
            "pages": pages}, ensure_ascii=False, sort_keys=True)
`, { role, paths, facts, ots, fb, fontJson, refs: refs || [], attachments: attachments !== false, profile: !!profile, level: level || "designer" });
    out.ms = Math.round(performance.now() - t0);
    return out;
  },

  async compare({ a, b }) {
    return runPy(`
import json
from core.inventory import compare
x = json.loads(ARGS)
json.dumps(compare(x["a"], x["b"]), ensure_ascii=False)
`, { a, b });
  },
};

const ready = boot();

self.onmessage = async (e) => {
  const { id, cmd, ...args } = e.data;
  try {
    await ready;
    const result = await commands[cmd](args);
    post({ id, ok: true, result });
  } catch (err) {
    post({ id, ok: false, error: String(err && err.message || err) });
  }
};

ready.catch((err) => post({ type: "fatal", error: String(err && err.message || err) }));
