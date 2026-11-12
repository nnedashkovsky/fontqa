"""Levels: what is checked, and how deep the report goes.

Designer   what concerns the drawing: character set and languages, outlines,
           metrics and kerning, OpenType features, family tests. The report
           shows measured and expected values, files and glyphs.
Engineer   everything, including what concerns the file: font tables, names,
           validators, lineages, variable-font tables, release and menus. The
           report adds how each check measures, check ids and the tables.

The level is chosen before a run (checks.in_level decides which checks run)
and is stored in issues.json; the report is drawn at that level. The Rules
page lets the reader switch between the two.

Page elements that only an engineer sees carry the class `l3`.
"""

import html

LEVELS = (("designer", "Designer"), ("engineer", "Engineer"))
DEFAULT_RUN = "engineer"     # terminal: the full inspection
DEFAULT_PAGE = "designer"    # the web page: the first choice for most people

# Shown as cards on the page, above the report and on the Rules page (after
# Font Analyzer's check picker). Keep in step with checks.DESIGNER.
INFO = {
    "designer": ("Mostly for type designers: what concerns the drawing", [
        "Overall info about the font",
        "Character set and language check",
        "Outlines: extremes, zero-length segments, coordinates",
        "Metrics and kerning overview",
        "OpenType features overview",
        "Family tests: same set, widths, vertical metrics, masters",
    ]),
    "engineer": ("Mostly for font engineers: what concerns the file", [
        "Everything in Designer",
        "Font tables: names, OS/2, head, post, meta, hinting",
        "Full family testing: lineages, variable vs static, instance names, STAT",
        "Validators: OTS, Font Bakery",
        "Release readiness and menu simulation",
        "How each check measures: tables, thresholds, tolerances",
    ]),
}

CSS = """<style>
html[data-level="designer"] .l3{display:none!important}
.levels{display:inline-flex;border:1px solid var(--line-2);border-radius:var(--r);overflow:hidden}
.levels button{border:0;background:transparent;padding:3px 10px;font-family:var(--mono);font-size:11px;color:var(--muted);cursor:pointer}
.levels button+button{border-left:1px solid var(--line-2)}
.levels button.on{background:var(--accent);color:var(--on-accent)}
.lvpanel{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:18px 0 6px}
.lvcard{text-align:left;font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:11px 14px 12px}
button.lvcard{cursor:pointer}button.lvcard:hover{border-color:var(--line-2)}
.lvcard.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);background:var(--accent-soft)}
.lvcard:not(.on).static{opacity:.6}
.lvcard .lt{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-weight:600;font-size:14px}
.lvcard .lt span{font-family:var(--mono);font-size:10.5px;font-weight:500;color:var(--accent)}
.lvcard .lw{font-size:12px;color:var(--muted);margin:2px 0 6px}
.lvcard ul{margin:0;padding-left:16px;font-size:12px;line-height:1.45;color:var(--ink-2)}.lvcard li{margin:1px 0}
.lvnote{font-size:12.5px;color:var(--muted);margin:4px 0 0}
@media (max-width:700px){.lvpanel{grid-template-columns:1fr}.lvcard:not(.on) ul{display:none}}
@media print{.levels,.lvpanel,.lvnote{display:none}}
</style>"""

# Rules page: the reader's choice, before the page paints
HEAD_SCRIPT = """<script>(function(){var l="%s";
try{l=localStorage.getItem("fontqa:level")||l}catch(e){}
var q=(location.search.match(/[?&]level=([a-z]+)/i)||[])[1];if(q)l=q.toLowerCase();
if(l!=="designer"&&l!=="engineer")l="%s";document.documentElement.dataset.level=l})();</script>""" % (DEFAULT_PAGE, DEFAULT_PAGE)

SWITCH = ('<div class="levels" role="group" aria-label="Level">'
          + "".join(f'<button type="button" data-level="{k}">{v}</button>' for k, v in LEVELS) + "</div>")

SCRIPT = """<script>(function(){
  var root=document.documentElement,sel=".levels button,button.lvcard";
  function mark(){document.querySelectorAll(sel).forEach(function(b){b.classList.toggle("on",b.dataset.level===root.dataset.level)})}
  document.querySelectorAll(sel).forEach(function(b){b.onclick=function(){
    root.dataset.level=b.dataset.level;try{localStorage.setItem("fontqa:level",b.dataset.level)}catch(e){}mark();
    if(window.onLevel)window.onLevel()}});
  mark();
})();</script>"""


def name(level):
    return dict(LEVELS).get(level, level)


def panel(current=None, interactive=True):
    """Level cards: who each level is for and what it checks. `current` marks one;
    interactive cards are buttons that switch the page."""
    cards = []
    for k, title in LEVELS:
        who, items = INFO[k]
        tag = "button" if interactive else "div"
        on = " on" if k == current else ""
        cards.append(f'<{tag} {"type=button " if interactive else ""}class="lvcard{on}{"" if interactive else " static"}" data-level="{k}">'
                     f'<div class="lt">{title}{"<span>this report</span>" if (k == current and not interactive) else ""}</div>'
                     f'<div class="lw">{html.escape(who)}</div>'
                     "<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + f"</ul></{tag}>")
    return '<div class="lvpanel" role="group" aria-label="Level">' + "".join(cards) + "</div>"


def head(html_head, level=None):
    """Level CSS into a page head. With `level`, the page is fixed at it (a report);
    without, the reader's choice is restored (the Rules page)."""
    if level:
        return html_head.replace('<html lang="en">', f'<html lang="en" data-level="{level}">', 1).replace("</head>", CSS + "</head>", 1)
    return html_head.replace("</head>", CSS + HEAD_SCRIPT + "</head>", 1)
