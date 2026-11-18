"""The Coverage part of the HTML report: character sets and languages as lists of bars.

Every row is a set or a language with the share the font has, as a bar, a percentage and a
count. A row with something missing opens a table of what to add (code point, Unicode name,
glyph name) and buttons that copy the glyph names (to paste into Glyphs' Add Glyphs), the
Unicode values or the characters. Above a list the same buttons copy the union for the rows
the filters leave visible, so "Windows code pages that are under 10 % short" becomes one
list to paste.

All numbers come from issues.json (`charsets`, `languages`); Unicode names and glyph names
are derived here, so the data stays small.
"""

import html
import unicodedata

from fontTools.agl import UV2AGL

from . import charsets as cs

REGIONS = (("EU", "Europe"), ("AS", "Asia"), ("AM", "Americas"), ("AF", "Africa"), ("OC", "Oceania"))
SHOWN_ROWS = 40  # rows of the table of missing glyphs; the copy buttons always take all of them
e = html.escape


def glyph_name(cp):
    """The name Glyphs and AGL use (Aacute), else uniXXXX / uXXXXX."""
    return UV2AGL.get(cp) or (f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}")


def uni(cp):
    return f"U+{cp:04X}"


SCRIPT_NAMES = {"Latn": "Latin", "Cyrl": "Cyrillic", "Grek": "Greek", "Arab": "Arabic", "Hebr": "Hebrew"}


# ------------------------------------------------------------------ one row

def row(name, meta, have, total, need, **data):
    """One list row. need: code points to add. data: filter attributes (script, group, regions, weight)."""
    pct = 100.0 * have / total if total else 0.0
    flag = "ok" if pct >= 100 else ("near" if pct >= 90 else "far")
    # the characters carry the code points; only the names AGL knows are written out, "~" stands for uniXXXX
    attrs = (f'data-name="{e(name.lower())}" ' + " ".join(f'data-{k}="{e(str(v))}"' for k, v in data.items()) +
             f' data-pct="{pct:.2f}" data-chars="{e("".join(chr(c) for c in need))}"'
             f' data-names="{e(" ".join(UV2AGL.get(c, "~") for c in need))}"')
    detail = ""
    if need:
        shown = need[:SHOWN_ROWS]
        # closing tags are optional in HTML; leaving them out halves the size of the tables
        rows = "".join(f"<tr><td class='lg'>{e(chr(c))}<td>{uni(c)}<td>{e(unicodedata.name(chr(c), ''))}<td>{e(glyph_name(c))}" for c in shown)
        more = (f"<p class='muted'>… and {len(need) - len(shown)} more; the copy buttons take all {len(need)}.</p>"
                if len(need) > len(shown) else "")
        detail = (f"<div class='ldet' hidden><table class='data'><tr><th><th>Unicode<th>Name<th>Glyph name"
                  f"{rows}</table>{more}<div class='lcopy'><button data-copy='names'>Copy glyph names</button>"
                  "<button data-copy='uni'>Copy Unicode values</button><button data-copy='chars'>Copy characters</button></div></div>")
    miss = f"<button class='lmiss'>missing {len(need)} ▸</button>" if need else "<span></span>"
    return (f"<div class='lrow {flag}' {attrs}><div class='ln'>{name_html(name, meta)}</div>"
            f"<div class='bar'><i style='width:{pct:.1f}%'></i></div>"
            f"<div class='lp'>{pct:.1f} % <small>({have}/{total})</small></div>{miss}{detail}</div>")


def name_html(name, meta):
    return f"{e(name)} <small>{e(meta)}</small>"


def chips(key, items):
    return "".join(f"<button data-f='{key}:{v}'>{e(label)}</button>" for v, label in items)


def filter_row(label, key, items, on="all"):
    return f"<div><span>{e(label)}</span><button data-f='{key}:all' class='on'>All</button>{chips(key, items)}</div>"


def group(title_html, intro, rows, filters, weight_label):
    sort = (("speakers" if weight_label == "Speakers" else "size", weight_label), ("name", "Name"))
    return (f"<div class='lang-group'><h3>{title_html}</h3><p>{intro}</p><div class='lfilters'>"
            + "".join(filters)
            + f"<div><span>Sort</span><button data-f='sort:coverage' class='on'>Coverage</button>{chips('sort', sort)}</div></div>"
            "<div class='lsum'><span class='lcount'></span><span class='lunion'>Code points to add for the rows shown: "
            "<b class='lneed'>0</b> <button data-union='names'>Copy glyph names</button><button data-union='uni'>Copy Unicode values</button>"
            f"<button data-union='chars'>Copy characters</button></span></div><div class='lrows'>{''.join(rows)}</div></div>")


def status_filter():
    return filter_row("Show", "status", (("ok", "Complete"), ("miss", "With missing"), ("near", "Under 10 % short")))


def styles_title(styles):
    return ", ".join(e(x) for x in styles[:6]) + (f" and {len(styles) - 6} more" if len(styles) > 6 else "")


# ------------------------------------------------------------------ character sets

def charsets_pane(cset):
    sets = cset["sets"]
    body = ""
    for g in cset["groups"]:
        rows = []
        for name, info in sets.items():
            miss = cs.expand(g["missing"].get(name, []))
            rows.append(row(name, f"{info['group']} · {info['total']} characters", g["have"][name], info["total"], miss,
                            script=info["script"], group=info["group"], size=info["total"]))
        scripts = [(s, SCRIPT_NAMES.get(s, s)) for s in sorted({i["script"] for i in sets.values()})]
        groups = [(x, x) for x in dict.fromkeys(i["group"] for i in sets.values())]
        full = sum(1 for n in sets if g["have"][n] == sets[n]["total"])
        body += group(styles_title(g["styles"]), f"<b>{full}</b> of {len(sets)} sets complete.", rows,
                      [status_filter(), filter_row("Script", "script", scripts) if len(scripts) > 1 else "",
                       filter_row("Source", "group", groups)], "Size")
    return body


# ------------------------------------------------------------------ languages

def languages_pane(langs):
    names, scripts = langs["names"], langs["scripts"]
    body = ""
    for g in langs["groups"]:
        rows = []
        for t in g["supported"]:
            n = names[t]
            rows.append(row(n["name"], f"{scripts.get(n['script'], n['script'])} · {n['speakers'] / 1e6:.1f} M", n["letters"], n["letters"], [],
                            script=n["script"], regions=" ".join(n["regions"]), speakers=n["speakers"]))
        for a in g["partial"]:
            n = names[a["tag"]]
            rows.append(row(n["name"], f"{scripts.get(n['script'], n['script'])} · {n['speakers'] / 1e6:.1f} M", a["have"], a["total"], a["need"],
                            script=n["script"], regions=" ".join(n["regions"]), speakers=n["speakers"]))
        every = g["supported"] + [a["tag"] for a in g["partial"]]
        present = sorted({names[t]["script"] for t in every})
        regions = [(c, n) for c, n in REGIONS if any(c in names[t]["regions"] for t in every)]
        filters = [status_filter()]
        if len(present) > 1:
            filters.append(filter_row("Script", "script", [(s, scripts.get(s, s)) for s in present]))
        if regions:
            filters.append(filter_row("Spoken in", "region", regions))
        body += group(styles_title(g["styles"]),
                      f"<b>{len(g['supported'])}</b> languages supported, <b>{len(g['partial'])}</b> more with at least 40 % of their letters.",
                      rows, filters, "Speakers")
    return body


# ------------------------------------------------------------------ the section

def section(r):
    cset, langs = r.get("charsets") or {}, r.get("languages") or {}
    panes = []
    if cset.get("groups"):
        panes.append(("sets", "Character sets", f"<p class='muted'>The share of each named set the font has. {e(cset['source'])}.</p>"
                      + charsets_pane(cset)))
    if langs.get("groups"):
        panes.append(("langs", "Languages", f"<p class='muted'>A language counts as supported when the font has all of its everyday letters, "
                      f"upper and lower case; the bar is the share of those letters. {e(langs['source'])}.</p>" + languages_pane(langs)))
    if not panes:
        return ""
    tabs = "".join(f"<button data-pane='{k}'{' class=on' if i == 0 else ''}>{label}</button>" for i, (k, label, _) in enumerate(panes))
    body = "".join(f"<div class='cpane' data-pane='{k}' id='{'languages' if k == 'langs' else 'charsets'}'{'' if i == 0 else ' hidden'}>{b}</div>"
                   for i, (k, _, b) in enumerate(panes))
    return f"<section id='coverage'><h2>Coverage</h2><div class='ctabs'>{tabs}</div>{body}{STYLE}{SCRIPT}</section>"


STYLE = """<style>
.ctabs{display:flex;gap:4px;margin:0 0 14px;border-bottom:1px solid var(--line)}
.ctabs button{border:0;background:transparent;font-family:var(--mono);font-size:12px;color:var(--muted);padding:7px 14px;border-bottom:2px solid transparent;margin-bottom:-1px;cursor:pointer}
.ctabs button.on{color:var(--accent);border-bottom-color:var(--accent)}
.lang-group{margin:0 0 28px}.lang-group h3{font-size:15px;margin:0 0 4px}.lang-group>p{margin:4px 0 10px;font-size:13px}
.lfilters{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}
.lfilters>div{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.lfilters span{width:78px;font-family:var(--mono);font-size:10.5px;color:var(--faint);text-transform:uppercase;letter-spacing:.06em}
.lang-group button{border:1px solid var(--line-2);background:var(--surface);border-radius:var(--r);padding:3px 9px;font-family:var(--mono);font-size:11px;color:var(--ink-2);cursor:pointer}
.lang-group button:hover{border-color:var(--accent)}.lang-group button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.lsum{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:0 0 8px;font-size:12.5px;color:var(--muted)}
.lunion button{margin-left:4px}
.lrows{border:1px solid var(--line);border-radius:var(--r);background:var(--surface);overflow:hidden}
.lrow{display:grid;grid-template-columns:minmax(150px,1.1fr) minmax(120px,2fr) 118px 112px;gap:10px;align-items:center;padding:7px 12px;border-top:1px solid var(--line);font-size:13px}
.lrow:first-child{border-top:0}.lrow small{color:var(--muted);font-family:var(--mono);font-size:10.5px}
.lrow .bar{height:7px;border-radius:4px;background:var(--sunken);overflow:hidden}.lrow .bar i{display:block;height:100%;background:var(--accent)}
.lrow.near .bar i{background:var(--warn)}.lrow.far .bar i{background:var(--faint)}
.lrow .lp{font-family:var(--mono);font-size:12px;text-align:right;white-space:nowrap}.lrow .lmiss{justify-self:end;white-space:nowrap}
.ldet{grid-column:1/-1;padding:6px 0 4px}.ldet table{width:auto;min-width:60%}.lg{font-size:20px;line-height:1}
.lcopy{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
@media (max-width:640px){.lrow{grid-template-columns:1fr 100px}.lrow .bar{grid-column:1/-1;order:3}}
@media print{.ctabs,.lfilters,.lunion,.lcopy,.lmiss{display:none}.ldet{display:block!important}.cpane[hidden]{display:block!important}}
</style>"""

SCRIPT = """<script>(function(){
function hex(c,n){var h=c.toString(16).toUpperCase();while(h.length<n)h="0"+h;return h}
function cps(d){return Array.from(d.chars||"").map(function(c){return c.codePointAt(0)})}
function glyph(c,n){return n&&n!=="~"?n:(c>0xFFFF?"u"+hex(c,5):"uni"+hex(c,4))}
function text(kind,list){ // list: [[code point, AGL name or ~]]
  if(kind==="uni")return list.map(function(x){return"U+"+hex(x[0],4)}).join(" ");
  if(kind==="chars")return list.map(function(x){return String.fromCodePoint(x[0])}).join("");
  return list.map(function(x){return glyph(x[0],x[1])}).join(" ")}
function rowList(d){var n=(d.names||"").split(" "),c=cps(d);return c.map(function(x,i){return[x,n[i]]})}
function copy(text,btn){
  var old=btn.textContent;
  function done(ok){btn.textContent=ok?"Copied":"Copy failed";setTimeout(function(){btn.textContent=old},1400)}
  function fallback(){var t=document.createElement("textarea");t.value=text;t.style.cssText="position:fixed;opacity:0";document.body.appendChild(t);t.select();
    var ok=false;try{ok=document.execCommand("copy")}catch(e){}document.body.removeChild(t);done(ok)}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){done(true)},fallback)}else fallback()
}
var cov=document.getElementById("coverage");
if(cov)cov.querySelector(".ctabs").addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;
  [].forEach.call(cov.querySelectorAll(".ctabs button"),function(x){x.classList.toggle("on",x===b)});
  [].forEach.call(cov.querySelectorAll(".cpane"),function(p){p.hidden=p.dataset.pane!==b.dataset.pane})});
document.querySelectorAll(".lang-group").forEach(function(g){
  var st={status:"all",script:"all",region:"all",group:"all",sort:"coverage"},box=g.querySelector(".lrows"),rows=[].slice.call(box.children);
  function apply(){
    var shown=0,need={};
    rows.forEach(function(r){var d=r.dataset,p=+d.pct,ok=true;
      if(st.status==="ok")ok=p>=100;else if(st.status==="miss")ok=p<100;else if(st.status==="near")ok=p>=90&&p<100;
      if(ok&&st.script!=="all")ok=d.script===st.script;
      if(ok&&st.group!=="all")ok=d.group===st.group;
      if(ok&&st.region!=="all")ok=(" "+d.regions+" ").indexOf(" "+st.region+" ")>=0;
      r.hidden=!ok;
      if(ok){shown++;rowList(d).forEach(function(x){need[x[0]]=x[1]})}});
    var w=function(r){return +(r.dataset.speakers||r.dataset.size||0)};
    var by={coverage:function(a,b){return b.dataset.pct-a.dataset.pct||w(b)-w(a)},
            speakers:function(a,b){return w(b)-w(a)},size:function(a,b){return w(b)-w(a)},
            name:function(a,b){return a.dataset.name<b.dataset.name?-1:1}}[st.sort];
    rows.slice().sort(by).forEach(function(r){box.appendChild(r)});
    var keys=Object.keys(need).map(Number).sort(function(a,b){return a-b}),list=keys.map(function(k){return[k,need[k]]});
    g._list=list;
    g.querySelector(".lcount").textContent=shown+" of "+rows.length+" shown";
    g.querySelector(".lneed").textContent=keys.length;
  }
  g.addEventListener("click",function(e){var b=e.target.closest&&e.target.closest("button");if(!b)return;
    if(b.dataset.f){var k=b.dataset.f.split(":");st[k[0]]=k[1];
      [].forEach.call(g.querySelectorAll("[data-f^='"+k[0]+":']"),function(x){x.classList.toggle("on",x===b)});apply();return}
    if(b.classList.contains("lmiss")){var d=b.parentNode.querySelector(".ldet");d.hidden=!d.hidden;return}
    if(b.dataset.copy){var r=b.closest(".lrow");copy(text(b.dataset.copy,rowList(r.dataset)),b);return}
    if(b.dataset.union){copy(text(b.dataset.union,g._list),b)}
  });
  apply();
});
})();</script>"""
