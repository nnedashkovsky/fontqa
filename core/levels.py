"""Levels of detail: one report, three depths.

Beginner   what is wrong, why it matters, what users see, what to do.
Designer   + measured and expected values, files, glyphs, the basis; the
           summary tables. The default.
Engineer   + how the check measures, classification and check ids, per-file
           values, the fonts table, the checks performed and the inputs.

Every element of a page is in the HTML at once; a class says from which level
it shows (`l2`, `l3`), and the level switcher only sets html[data-level]. So a
printout or a saved page keeps whatever level was chosen, and nothing is
generated twice. The choice is remembered per browser and can be set by the
URL: report.html?level=beginner.
"""

LEVELS = (("1", "Beginner"), ("2", "Designer"), ("3", "Engineer"))
DEFAULT = "2"

# Shown as cards above the report and the Rules page, after Font Analyzer's
# check picker: who the level is for and what it adds. Keep in step with the
# l2/l3 classes in report_html.py and rules.SECTION_LEVEL.
INFO = {
    "report": {
        "1": ("Mostly for anyone new to font files", [
            "What is wrong, in plain words",
            "Why it matters and what users will see",
            "What to do about it",
            "Only issues to fix or confirm; harmless differences hidden",
        ]),
        "2": ("Mostly for type designers", [
            "Everything in Beginner",
            "Measured and expected values, files, glyphs",
            "Harmless differences too",
            "Summary by category, predicted symptoms, character set coverage",
            "Attachments: glyph grid, GSUB, proofs, menus",
        ]),
        "3": ("Mostly for font engineers", [
            "Everything in Designer",
            "How each check measures: tables, thresholds, tolerances",
            "Check ids and classification, linked to the rules",
            "Key table values of every file",
            "Checks performed, inputs with SHA-256",
        ]),
    },
    "rules": {
        "1": ("Mostly for anyone new to font files", [
            "What each rule checks",
            "Why it matters and what users will see",
            "How to fix it",
        ]),
        "2": ("Mostly for type designers", [
            "Everything in Beginner",
            "When a rule does not apply",
            "Examples: bad and good",
            "Which fonts it applies to, related rules",
        ]),
        "3": ("Mostly for font engineers", [
            "Everything in Designer",
            "How each check measures: tables, thresholds, tolerances",
            "Sources: specifications and vendor documents",
        ]),
    },
}

CSS = """<style>
html[data-level="1"] .l2,html[data-level="1"] .l3,html[data-level="2"] .l3{display:none!important}
html[data-level="1"] .l1-hide{display:none!important}
html:not([data-level="1"]) .l1-only{display:none!important}
.levels{display:inline-flex;border:1px solid var(--line-2);border-radius:var(--r);overflow:hidden}
.levels button{border:0;background:transparent;padding:3px 10px;font-family:var(--mono);font-size:11px;color:var(--muted);cursor:pointer}
.levels button+button{border-left:1px solid var(--line-2)}
.levels button.on{background:var(--accent);color:var(--on-accent)}
.lvpanel{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0 6px}
.lvcard{text-align:left;font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:11px 14px 12px;cursor:pointer}
.lvcard:hover{border-color:var(--line-2)}
.lvcard.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);background:var(--accent-soft)}
.lvcard .lt{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-weight:600;font-size:14px}
.lvcard .lt span{font-family:var(--mono);font-size:10.5px;font-weight:500;color:var(--accent)}
.lvcard .lw{font-size:12px;color:var(--muted);margin:2px 0 6px}
.lvcard ul{margin:0;padding-left:16px;font-size:12px;line-height:1.45;color:var(--ink-2)}.lvcard li{margin:1px 0}
@media (max-width:700px){.lvpanel{grid-template-columns:1fr}.lvcard:not(.on) ul{display:none}}
@media print{.levels,.lvpanel{display:none}}
</style>"""

# set the level before the page paints, so it does not flash at the default
HEAD_SCRIPT = """<script>(function(){var l="%s",m={beginner:"1",designer:"2",engineer:"3"};
try{l=localStorage.getItem("fontqa:level")||l}catch(e){}
var q=(location.search.match(/[?&]level=([a-z0-9]+)/i)||[])[1];if(q)l=m[q.toLowerCase()]||q;
if(!/^[123]$/.test(l))l="%s";document.documentElement.dataset.level=l})();</script>""" % (DEFAULT, DEFAULT)

SWITCH = ('<div class="levels" role="group" aria-label="Level of detail">'
          + "".join(f'<button type="button" data-level="{k}">{v}</button>' for k, v in LEVELS) + "</div>")

def panel(kind="report"):
    """Level cards: who each level is for and what it shows. A card click sets the level."""
    import html
    cards = []
    for k, name in LEVELS:
        who, items = INFO[kind][k]
        cards.append(f'<button type="button" class="lvcard" data-level="{k}"><div class="lt">{name}'
                     f'{"<span>default</span>" if k == DEFAULT else ""}</div><div class="lw">{html.escape(who)}</div>'
                     "<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul></button>")
    return '<div class="lvpanel" role="group" aria-label="Level of detail">' + "".join(cards) + "</div>"


SCRIPT = """<script>(function(){
  var root=document.documentElement,sel=".levels button,.lvcard";
  function mark(){document.querySelectorAll(sel).forEach(function(b){b.classList.toggle("on",b.dataset.level===root.dataset.level)})}
  document.querySelectorAll(sel).forEach(function(b){b.onclick=function(){
    root.dataset.level=b.dataset.level;try{localStorage.setItem("fontqa:level",b.dataset.level)}catch(e){}mark();
    if(window.onLevel)window.onLevel()}});
  mark();
})();</script>"""


def head(html_head):
    """Insert the level CSS and the early script into a page head."""
    return html_head.replace("</head>", CSS + HEAD_SCRIPT + "</head>", 1)
