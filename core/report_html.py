"""issues.json -> one self-contained HTML report (English).

Built after RT's summary report: scope and its limits first, the legend, a
matrix of categories, what was confirmed normal, then one card per issue with
measured vs expected, basis, files, glyphs and fix direction. Unlike RT's
English PDF, nothing here is retyped: every word comes from issues.json, so
another language later is another template over the same data.

The page uses IBM Plex, Instrument Serif, a green accent,
light and dark themes, filters issues in place, and prints to PDF.
"""

import html

from . import VERSION, levels
from .rules import RULES_URL, markdown

ACTION_LABEL = {"fix": "Fix", "confirm": "Confirm", "ok": "Harmless"}
LEGEND = {
    "Action": [
        ("Fix", "Fixing the font data removes the problem for users or the difference from the specification."),
        ("Confirm", "Possibly intentional. Confirm the intent; if it is deliberate, nothing needs to change."),
        ("Harmless", "Differs from the expected value but does no harm in use or compatibility. No fix needed."),
    ],
    "Severity": [
        ("High", "A style cannot be selected, or glyphs do not render as intended, in major environments."),
        ("Medium", "Affects display or selection in some environments or uses, or values disagree between styles, lineages or formats."),
        ("Low", "Values or descriptions differ without an expected effect on display or typesetting."),
    ],
    "Judgment": [
        ("×", "Does not match the expected value (specification, studio rule, or store requirement)."),
        ("△", "Needs confirmation: the expected value is ambiguous or depends on intent."),
        ("○", "Matches."),
        ("—", "Not applicable or not performed."),
    ],
}


def e(s):
    return html.escape("" if s is None else str(s))


def render(r, extra="", attachments=()):
    """`extra`: HTML sections inserted before Inputs (the specimen); `attachments`: file names to link."""
    s = r["summary"]
    issues = r["issues"]
    cats = r["categories"]
    parts = [levels.head(HEAD.replace("{{title}}", e(r["title"] or "Inspection")))]
    parts.append(f"""<div class="wrap">
<header>
  <div><div class="kicker">Inspection report</div><h1>{e(r['title'] or 'Fonts')}</h1>
  <div class="sub">{e(r['date'])} · profile {e(r['profile'])} · {r['inventory']['files']} files · Font QA core {e(r['environment']['core'])}</div></div>
  <div class="tally">
    <div><div class="v fix">{s['by_action']['fix']}</div><div class="k">fix</div></div>
    <div><div class="v confirm">{s['by_action']['confirm']}</div><div class="k">confirm</div></div>
    <div><div class="v">{s['by_action']['ok']}</div><div class="k">harmless</div></div>
    <div><div class="v">{s['symptoms']}</div><div class="k">predicted symptoms</div></div>
    <div class="ctl">{levels.SWITCH}<button class="theme" id="theme">auto</button></div>
  </div>
</header>""" + levels.panel("report"))

    # ---- scope
    inv = r["inventory"]
    kv = lambda d: " · ".join(f"{k} {v}" for k, v in d.items())
    opts = r["options"]
    performed = [
        ("Machine inspection", f"{len(r['checks'])} checks over {inv['fonts']} readable files"
         + (f", {inv['errors']} unreadable" if inv["errors"] else "")),
        ("OTS (browser acceptance)", "browser font loader" if r["environment"]["env"] == "browser" and opts.get("ots")
         else ("ots module" if opts.get("ots") else "not performed")),
        ("Font Bakery", "universal profile" if opts.get("fontbakery") else "not performed"),
        ("Promo facts", "design/font.json compared" if opts.get("font_json") else "no font.json given"),
    ]
    parts.append(f"""<section><h2>Scope</h2>
<div class="grid2">
<table class="kv"><tr><th>Files</th><td>{e(kv(inv['formats']))}<br>{e(_lineages(inv['lineages']))}</td></tr>
<tr><th>Families</th><td>{inv['families']} · {inv['variable']} variable</td></tr>
<tr class="l3"><th>Environment</th><td>{e(r['environment']['env'])} · Python {e(r['environment']['python'])} · fontTools {e(r['environment']['fontTools'])}</td></tr></table>
<table class="kv">{''.join(f'<tr><th>{e(a)}</th><td>{e(b)}</td></tr>' for a, b in performed)}</table>
</div>
{f'<p class="note">Not performed (input not given): {e(", ".join(s["not_performed"]))}.</p>' if s['not_performed'] else ''}
{f'<p class="muted">Not applicable to these files: {e(", ".join(s["not_applicable"]))}.</p>' if s.get('not_applicable') else ''}
{''.join(f'<p class="note">Check error — {e(x["check"])}: {e(x["error"])}</p>' for x in r['errors'])}
<p class="muted l2">Each issue lists expected and measured values, the basis for comparison, the files and glyphs concerned, and a suggested fix direction. The report states facts about the received files; it does not judge design intent.</p>
</section>""")

    # ---- legend
    parts.append('<section><h2>Legend</h2><div class="grid3">' + "".join(
        f'<table class="legend"><tr><th colspan="2">{e(axis)}</th></tr>' +
        "".join(f"<tr><td class='lv'>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in rows) + "</table>"
        for axis, rows in LEGEND.items()) + "</div></section>")

    # ---- summary matrix
    rows = []
    for cat, name in cats.items():
        b = s["by_category"][cat]
        if not b["checks"]:
            continue
        confirmed = b["confirmed"]
        rows.append(f"""<tr><td><b>{e(cat)}</b> {e(name)}</td><td class="n fix">{b['fix'] or ''}</td><td class="n confirm">{b['confirm'] or ''}</td>
<td class="n">{b['ok'] or ''}</td><td class="n">{b['symptoms'] or ''}</td><td class="n muted">{b['checks']}</td>
<td class="ok-list">{e('; '.join(confirmed)) if confirmed else '<span class="muted">—</span>'}</td></tr>""")
    parts.append(f"""<section class="l2"><h2>Summary of results</h2>
<div class="scroll"><table class="matrix"><tr><th>Category</th><th>Fix</th><th>Confirm</th><th>Harmless</th><th>Symptoms</th><th>Checks</th><th>Confirmed normal</th></tr>
{''.join(rows)}</table></div></section>""")

    # ---- issues
    filt = "".join(f'<button data-f="action:{a}">{ACTION_LABEL[a]}</button>' for a in ("fix", "confirm", "ok"))
    filt += "".join(f'<button data-f="severity:{x}">{x.title()}</button>' for x in ("high", "medium", "low"))
    filt += "".join(f'<button data-f="category:{c}">{c}</button>' for c in cats if s["by_category"][c]["checks"])
    n_ok = sum(1 for i in issues if i["action"] == "ok")
    hidden_note = (f'<p class="muted l1-only">{n_ok} harmless difference{"s" if n_ok != 1 else ""} hidden at this level; '
                   f'switch to Designer to see {"them" if n_ok != 1 else "it"}.</p>') if n_ok else ""
    parts.append(f"""<section><h2>Issues <span class="count">{len(issues)}</span></h2>
<div class="filters"><span class="l2 fb">{filt}</span><input id="q" type="search" placeholder="Search issues, files, glyphs"></div>
{hidden_note}<div id="issues">{''.join(_card(i, r) for i in issues) or '<p class="muted">No issues.</p>'}</div></section>""")

    # ---- symptoms
    if r["symptoms"]:
        parts.append("""<section class="l2"><h2>Predicted symptoms</h2><p class="muted">What users would see, derived from the parent issue.
Status "predicted" means not yet observed in the environment; confirm with screenshots.</p><div class="scroll"><table class="data">
<tr><th>No.</th><th>Environment</th><th>Symptom</th><th>Parent</th><th>Status</th></tr>""" + "".join(
            f"<tr><td>{e(x['id'])}</td><td>{e(x['environment'])}</td><td>{e(x['symptom'])}</td>"
            f"<td><a href='#{e(x['parent'])}'>{e(x['parent'])}</a></td><td>{e(x['status'])}</td></tr>" for x in r["symptoms"])
            + "</table></div></section>")

    # ---- coverage
    if r["coverage"]:
        names = list(r["coverage"][0]["sets"])
        head = "".join(f"<th>{e(n)}</th>" for n in names)
        body = ""
        for c in r["coverage"]:
            cells = ""
            for n in names:
                have, total = c["sets"][n]
                full = have == total
                cells += f"<td class='n {'okc' if full else ''}'>{'✓' if full else f'{have}/{total}'}</td>"
            nxt = f"<details><summary>{len(c['missing_for_next'])} to {e(c['next_level'])}</summary><code>{e(' '.join(c['missing_for_next']))}</code></details>" if c["next_level"] else "complete"
            body += f"<tr><td>{e(c['family'])} <b>{e(c['style'])}</b></td>{cells}<td>{nxt}</td></tr>"
        parts.append(f"""<section class="l2"><h2>Character set coverage</h2><div class="scroll"><table class="data"><tr><th>Style</th>{head}<th>Next level</th></tr>{body}</table></div></section>""")

    # ---- fonts table
    fields = r["fonts"]["fields"]
    trs = ""
    for row in r["fonts"]["rows"]:
        tds = "".join(f"<td class='{'out' if k in row['outliers'] else ''}'>{e(row['values'][k])}</td>" for k in fields)
        trs += f"<tr><td class='path'>{e(row['path'])}</td><td>{e(row['lineage'])} {e(row['format'])}</td>{tds}</tr>"
    parts.append(f"""<section class="l3"><h2>Fonts</h2><p class="muted">Key values per file. Highlighted cells differ from the rest of their family and lineage.</p>
<div class="scroll"><table class="data fonts"><tr><th>File</th><th>Lineage</th>{''.join(f'<th>{e(k)}</th>' for k in fields)}</tr>{trs}</table></div></section>""")

    # ---- checks performed
    trs = "".join(f"""<tr><td>{e(c['category'])}</td><td><b>{e(c['title'])}</b><div class="muted">{e(c['what'])}</div></td>
<td class="n">{c['files_passed']}</td><td class="n {'fix' if c['files_flagged'] else ''}">{c['files_flagged'] or ''}</td><td class="n muted">{c['files_na'] or ''}</td></tr>""" for c in r["checks"])
    parts.append(f"""<section class="l3"><h2>Checks performed</h2><div class="scroll"><table class="data"><tr><th></th><th>Check</th><th>Passed</th><th>Flagged</th><th>N/A</th></tr>{trs}</table></div></section>""")

    # ---- inputs
    trs = "".join(f"<tr><td class='path'>{e(x['path'])}</td><td>{e(x['lineage'] or '—')} {e(x['format'])}</td><td class='n'>{x['size']:,}</td><td><code>{e(x['sha256'][:16])}…</code></td></tr>" for x in r["inputs"])
    if attachments:
        parts.append("<section class='l2'><h2>Attachments</h2><p>" + " · ".join(
            f"<a href='{e(a)}'>{e(a)}</a>" for a in attachments) + "</p><p class='muted'>Material without judgements, "
            "glyph comparison with the references, the GSUB listing, proofs. Each prints to PDF.</p></section>")
    parts.append(extra)
    parts.append(f"""<section><h2 class="l3">Inputs</h2><details class="l3"><summary>{len(r['inputs'])} files with SHA-256</summary><div class="scroll"><table class="data">
<tr><th>File</th><th>Lineage</th><th>Bytes</th><th>SHA-256</th></tr>{trs}</table></div></details>
<p class="muted foot">Generated by Font QA core {e(VERSION)} on {e(r['date'])} · issues.json is the source of this page and of report.xlsx.</p></section></div>""")
    parts.append(SCRIPT + levels.SCRIPT)
    return "".join(parts)


def _lineages(d):
    """'App 50 · Desktop 50 · Web 98'; files outside such folders are 'not in App/Desktop/Web folders'."""
    parts = [f"{k} {v}" for k, v in d.items() if k != "—"]
    if "—" in d:
        parts.append(f"{d['—']} not in App/Desktop/Web folders")
    return " · ".join(parts)


def _card(i, r):
    files = i["files"]
    by_file = i["measured_by_file"]
    glyphs = i["glyphs"]
    gl = ""
    if glyphs:
        shown = "".join(f"<span class='g'>{e(g)}</span>" for g in glyphs[:40])
        more = "".join(f"<span class='g'>{e(g)}</span>" for g in glyphs[40:])
        gl = f"<tr class='l2'><th>Glyphs</th><td><div class='gs'>{shown}</div>" + (
            f"<details><summary>{i['glyph_count'] - 40} more</summary><div class='gs'>{more}</div></details>" if more else "") + "</td></tr>"
    measured = e(i["measured"])
    if by_file:
        measured += "<details><summary>per file</summary><table class='mini'>" + "".join(
            f"<tr><td class='path'>{e(f)}</td><td>{e(m)}</td></tr>" for f, m in by_file.items()) + "</table></details>"
    syms = [s for s in r["symptoms"] if s["parent"] == i["id"]]
    sym = ("<tr><th>Symptoms</th><td>" + "<br>".join(f"{e(s['id'])} · {e(s['environment'])}{': ' if s['environment'] else ''}{e(s['symptom'])} <span class='muted'>(predicted)</span>" for s in syms) + "</td></tr>") if syms else ""
    rule = i.get("rule") or {}
    why = (f"<tr><th>Why it matters</th><td><div class='md'>{markdown(rule['why'])}</div></td></tr>" if rule.get("why")
           else f"<tr><th>Why it matters</th><td>{e(i['basis'])}</td></tr>")
    how = f"<tr class='l3'><th>How it is checked</th><td><div class='md'>{markdown(rule['how'])}</div></td></tr>" if rule.get("how") else ""
    basis = f"<tr class='l2'><th>Basis</th><td>{e(i['basis'])}</td></tr>" if rule.get("why") else ""
    search = " ".join([i["id"], i["summary"], i["check"], i["classification"], " ".join(files), " ".join(glyphs[:200])]).lower()
    return f"""<article class="issue a-{i['action']}{' l2' if i['action'] == 'ok' else ''}" id="{e(i['id'])}" data-action="{i['action']}" data-severity="{i['severity']}" data-category="{i['category']}" data-search="{e(search)}">
<div class="ih"><span class="no">{e(i['id'])}</span><span class="tag {i['action']}">{ACTION_LABEL[i['action']]}</span><span class="tag sev-{i['severity']}">{i['severity'].title()}</span><span class="j l2">{e(i['judgment'])}</span><span class="cls l3">{e(i['category'])} · {e(i['classification'])} · <a href="{RULES_URL}#{e(i['check'])}"><code>{e(i['check'])}</code></a></span><a class="rl" href="{RULES_URL}#{e(i['check'])}">rule</a></div>
<h3>{e(i['summary'])}</h3>
<table class="kv">
{why}
<tr class="l2"><th>Measured</th><td>{measured}</td></tr>
<tr class="l2"><th>Expected</th><td>{e(i['expected'])}</td></tr>
<tr class="l2"><th>Files</th><td>{e(i['files_summary'])}<details><summary>{len(files)} files</summary><div class="paths">{'<br>'.join(e(f) for f in files)}</div></details></td></tr>
{gl}
{basis}
<tr><th>Fix direction</th><td>{e(i['fix'])}</td></tr>
{sym}
{how}
</table></article>"""


HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}} — inspection</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=Instrument+Serif&display=swap">
<style>
:root{--bg:#F3F5F4;--surface:#FFF;--surface-2:#F8FAF9;--sunken:#E8ECEA;--ink:#15191A;--ink-2:#3B4446;--muted:#5E696B;--faint:#8B9698;
--line:#DCE2E0;--line-2:#C7CFCD;--accent:#1F6F5C;--accent-soft:#E0EFE9;--on-accent:#fff;--warn:#A85B14;--warn-soft:#FAEEE0;--bad:#B23A2E;--bad-soft:#F8E4E1;
--sans:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace;--serif:"Instrument Serif",Georgia,serif;--r:7px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0D100F;--surface:#161A19;--surface-2:#1B201F;--sunken:#0A0D0C;--ink:#E5EAE8;--ink-2:#BCC5C3;
--muted:#8C9795;--faint:#6C7775;--line:#252B2A;--line-2:#333B39;--accent:#4FBF9F;--accent-soft:#0F2A24;--on-accent:#05211A;--warn:#D69049;--warn-soft:#2E2211;--bad:#E07A6E;--bad-soft:#2F1714}}
:root[data-theme="dark"]{--bg:#0D100F;--surface:#161A19;--surface-2:#1B201F;--sunken:#0A0D0C;--ink:#E5EAE8;--ink-2:#BCC5C3;--muted:#8C9795;--faint:#6C7775;
--line:#252B2A;--line-2:#333B39;--accent:#4FBF9F;--accent-soft:#0F2A24;--on-accent:#05211A;--warn:#D69049;--warn-soft:#2E2211;--bad:#E07A6E;--bad-soft:#2F1714}
*{box-sizing:border-box}[hidden]{display:none!important}
html{background:var(--bg)}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:26px 24px 70px}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;padding-bottom:16px;border-bottom:1px solid var(--line);margin-bottom:8px}
.kicker{font-size:10.5px;font-weight:600;letter-spacing:.11em;text-transform:uppercase;color:var(--faint)}
h1{font-family:var(--serif);font-size:38px;font-weight:400;line-height:1.05;margin:2px 0 0}
.sub{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin-top:6px}
.tally{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-end}.tally div{text-align:right}
.tally .v{font-family:var(--mono);font-size:24px;font-weight:500;font-variant-numeric:tabular-nums}.tally .k{font-size:10.5px;color:var(--muted)}
.v.fix,.n.fix{color:var(--bad)}.v.confirm,.n.confirm{color:var(--warn)}
.theme{border:1px solid var(--line-2);background:transparent;border-radius:var(--r);padding:3px 8px;font-family:var(--mono);font-size:11px;color:var(--muted);cursor:pointer}
section{margin-top:30px}
h2{font-size:10.5px;font-weight:600;letter-spacing:.11em;text-transform:uppercase;color:var(--faint);margin:0 0 10px}
h2 .count{color:var(--ink-2);margin-left:6px}
.muted{color:var(--muted)}.note{font-size:12.5px;color:var(--warn);background:var(--warn-soft);border-radius:var(--r);padding:7px 11px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media (max-width:860px){.grid2,.grid3{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%}
.kv th{text-align:left;vertical-align:top;font-weight:500;color:var(--muted);font-size:12px;padding:5px 12px 5px 0;width:36%}
.issue .kv th{width:120px;white-space:nowrap}.kv td{overflow-wrap:anywhere}
.kv td{padding:5px 0;vertical-align:top}
.grid2>.kv,.legend,.scroll{background:var(--surface);border:1px solid var(--line);border-radius:var(--r)}
.grid2>.kv{padding:8px 14px}
.legend th{text-align:left;padding:9px 12px;font-size:12px;border-bottom:1px solid var(--line)}
.legend td{padding:6px 12px;border-top:1px solid var(--line);font-size:12.5px;vertical-align:top}.legend .lv{font-weight:600;white-space:nowrap;font-family:var(--mono)}
.scroll{overflow-x:auto}
.matrix th,.data th{text-align:left;font-size:11px;font-weight:600;color:var(--muted);padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.matrix td,.data td{padding:7px 10px;border-top:1px solid var(--line);vertical-align:top;font-size:12.5px}
td.n{font-family:var(--mono);text-align:right;font-variant-numeric:tabular-nums;width:70px}
.ok-list{font-size:11.5px;color:var(--muted)}
.okc{color:var(--accent)}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.filters button{border:1px solid var(--line-2);background:var(--surface);border-radius:var(--r);padding:4px 10px;font-family:var(--mono);font-size:11.5px;color:var(--ink-2);cursor:pointer}
.filters button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.filters input{flex:1;min-width:200px;border:1px solid var(--line-2);background:var(--surface);color:var(--ink);border-radius:var(--r);padding:4px 10px;font:inherit;font-size:12.5px}
.issue{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--line-2);border-radius:var(--r);padding:14px 16px;margin-bottom:12px}
.issue.a-fix{border-left-color:var(--bad)}.issue.a-confirm{border-left-color:var(--warn)}
.ih{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-family:var(--mono);font-size:11px}
.ih .no{font-weight:600;color:var(--ink)}.ih .cls{color:var(--muted)}.ih .j{font-size:13px}
.tag{border-radius:4px;padding:1px 7px;font-weight:500}
.tag.fix{background:var(--bad-soft);color:var(--bad)}.tag.confirm{background:var(--warn-soft);color:var(--warn)}.tag.ok{background:var(--accent-soft);color:var(--accent)}
.tag.sev-high{border:1px solid var(--bad);color:var(--bad)}.tag.sev-medium{border:1px solid var(--warn);color:var(--warn)}.tag.sev-low{border:1px solid var(--line-2);color:var(--muted)}
.issue h3{font-size:16px;font-weight:600;margin:8px 0 8px;text-wrap:balance}
.gs{display:flex;flex-wrap:wrap;gap:4px}.g{font-family:var(--mono);font-size:11px;background:var(--sunken);border-radius:4px;padding:1px 6px}
details summary{cursor:pointer;font-family:var(--mono);font-size:11px;color:var(--faint);margin-top:3px}
.paths,.path{font-family:var(--mono);font-size:11px;word-break:break-all}
table.mini td{padding:2px 8px 2px 0;font-size:11.5px;border-top:1px solid var(--line)}
.fonts td{white-space:nowrap;font-family:var(--mono);font-size:11px}.fonts td.out{background:var(--warn-soft);color:var(--warn);font-weight:600}
code{font-family:var(--mono);font-size:11px;word-break:break-all}
a{color:var(--accent)}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.fb{display:contents}
.ih .rl{margin-left:auto;font-family:var(--sans);font-size:12px}
.issue .md p{margin:0 0 6px}.issue .md ul,.issue .md ol{margin:0 0 6px;padding-left:18px}.issue .md li{margin:2px 0}.issue .md .tw{margin:4px 0}
.issue .md table th,.issue .md table td{font-size:12px;padding:3px 10px 3px 0;border-top:1px solid var(--line);text-align:left}
.foot{margin-top:24px;font-size:11.5px}
@media (max-width:600px){.wrap{padding:18px 16px 60px}.kv tr{display:block;padding:3px 0}.kv th,.kv td,.issue .kv th{display:block;width:auto;padding:1px 0;white-space:normal}.tally{gap:14px}}
@media print{.filters,.theme{display:none}body{background:#fff}.issue{break-inside:avoid}details{display:block}}
</style></head><body>"""

SCRIPT = """<script>
(function(){
  var THEMES=["auto","light","dark"],t="auto";
  try{t=localStorage.getItem("fontqa:theme")||"auto"}catch(e){}
  function apply(x){if(x==="auto")delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=x;document.getElementById("theme").textContent=x}
  apply(t);
  document.getElementById("theme").onclick=function(){t=THEMES[(THEMES.indexOf(t)+1)%3];apply(t);try{localStorage.setItem("fontqa:theme",t)}catch(e){}};
  var on={};
  function run(){
    var q=(document.getElementById("q").value||"").toLowerCase();
    document.querySelectorAll(".issue").forEach(function(el){
      var ok=true;
      ["action","severity","category"].forEach(function(k){var s=on[k];if(s&&s.size&&!s.has(el.dataset[k]))ok=false});
      if(q&&el.dataset.search.indexOf(q)<0)ok=false;
      el.hidden=!ok;
    });
  }
  document.querySelectorAll(".filters button").forEach(function(b){
    b.onclick=function(){var p=b.dataset.f.split(":"),k=p[0],v=p[1];on[k]=on[k]||new Set();
      if(on[k].has(v)){on[k].delete(v);b.classList.remove("on")}else{on[k].add(v);b.classList.add("on")}run()};
  });
  document.getElementById("q").oninput=run;
})();
</script></body></html>"""
