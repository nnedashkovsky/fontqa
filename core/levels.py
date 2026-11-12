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

CSS = """<style>
html[data-level="1"] .l2,html[data-level="1"] .l3,html[data-level="2"] .l3{display:none!important}
html[data-level="1"] .l1-hide{display:none!important}
html:not([data-level="1"]) .l1-only{display:none!important}
.levels{display:inline-flex;border:1px solid var(--line-2);border-radius:var(--r);overflow:hidden}
.levels button{border:0;background:transparent;padding:3px 10px;font-family:var(--mono);font-size:11px;color:var(--muted);cursor:pointer}
.levels button+button{border-left:1px solid var(--line-2)}
.levels button.on{background:var(--accent);color:var(--on-accent)}
@media print{.levels{display:none}}
</style>"""

# set the level before the page paints, so it does not flash at the default
HEAD_SCRIPT = """<script>(function(){var l="%s",m={beginner:"1",designer:"2",engineer:"3"};
try{l=localStorage.getItem("fontqa:level")||l}catch(e){}
var q=(location.search.match(/[?&]level=([a-z0-9]+)/i)||[])[1];if(q)l=m[q.toLowerCase()]||q;
if(!/^[123]$/.test(l))l="%s";document.documentElement.dataset.level=l})();</script>""" % (DEFAULT, DEFAULT)

SWITCH = ('<div class="levels" role="group" aria-label="Level of detail">'
          + "".join(f'<button type="button" data-level="{k}">{v}</button>' for k, v in LEVELS) + "</div>")

SCRIPT = """<script>(function(){
  var root=document.documentElement;
  function mark(){document.querySelectorAll(".levels button").forEach(function(b){b.classList.toggle("on",b.dataset.level===root.dataset.level)})}
  document.querySelectorAll(".levels button").forEach(function(b){b.onclick=function(){
    root.dataset.level=b.dataset.level;try{localStorage.setItem("fontqa:level",b.dataset.level)}catch(e){}mark();
    if(window.onLevel)window.onLevel()}});
  mark();
})();</script>"""


def head(html_head):
    """Insert the level CSS and the early script into a page head."""
    return html_head.replace("</head>", CSS + HEAD_SCRIPT + "</head>", 1)
