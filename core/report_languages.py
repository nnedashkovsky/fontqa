"""The Languages part of the HTML report: a bar for every language, filters, what to add.

Each language that the font supports, or is short of by at most 60%, is a row: name,
script, a bar with the share of its letters the font has, and the count. A language
with missing letters opens a table of what to add (code point, Unicode name, glyph
name) with buttons that copy the glyph names (to paste into Glyphs' Add Glyphs), the
Unicode values or the characters. The same buttons above the list copy the union for
the languages that the filters leave visible: pick Europe and "under 10 % short",
and one click gives the letters that open the most languages.

All data comes from issues.json (`languages`); the Unicode names and glyph names are
derived here, so the data stays small.
"""

import html
import unicodedata

from fontTools.agl import UV2AGL

REGIONS = (("EU", "Europe"), ("AS", "Asia"), ("AM", "Americas"), ("AF", "Africa"), ("OC", "Oceania"))
e = html.escape


def glyph_name(cp):
    """The name Glyphs and AGL use (Aacute), else uniXXXX / uXXXXX."""
    return UV2AGL.get(cp) or (f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}")


def uni(cp):
    return f"U+{cp:04X}"


def _row(tag, info, scripts, item):
    """One language. item: None for a supported language, else {"need", "have", "total"}."""
    have, total = (item["have"], item["total"]) if item else (info["letters"], info["letters"])
    pct = 100.0 * have / total
    need = item["need"] if item else []
    flag = "ok" if pct >= 100 else ("near" if pct >= 90 else "far")
    data = (f'data-name="{e(info["name"].lower())}" data-script="{e(info["script"])}" data-regions="{e(" ".join(info["regions"]))}" '
            f'data-pct="{pct:.2f}" data-speakers="{info["speakers"]}" '
            f'data-uni="{e(" ".join(uni(c) for c in need))}" data-names="{e(" ".join(glyph_name(c) for c in need))}" '
            f'data-chars="{e("".join(chr(c) for c in need))}"')
    detail = ""
    if need:
        rows = "".join(
            f"<tr><td class='lg'>{e(chr(c))}</td><td><code>{uni(c)}</code></td>"
            f"<td>{e(unicodedata.name(chr(c), ''))}</td><td><code>{e(glyph_name(c))}</code></td></tr>" for c in need)
        detail = (f"<div class='ldet' hidden><table class='data'><tr><th></th><th>Unicode</th><th>Name</th><th>Glyph name</th></tr>{rows}</table>"
                  "<div class='lcopy'><button data-copy='names'>Copy glyph names</button><button data-copy='uni'>Copy Unicode values</button>"
                  "<button data-copy='chars'>Copy characters</button></div></div>")
    miss = f"<button class='lmiss'>missing {len(need)} ▸</button>" if need else "<span></span>"
    return (f"<div class='lrow {flag}' {data}><div class='ln'>{e(info['name'])} <small>{e(scripts.get(info['script'], info['script']))}"
            f" · {info['speakers'] / 1e6:.1f} M</small></div><div class='bar'><i style='width:{pct:.1f}%'></i></div>"
            f"<div class='lp'>{pct:.1f} % <small>({have}/{total})</small></div>{miss}{detail}</div>")


def section(langs):
    names, scripts = langs["names"], langs["scripts"]
    body = ""
    for g in langs["groups"]:
        rows = [_row(t, names[t], scripts, None) for t in g["supported"]]
        rows += [_row(a["tag"], names[a["tag"]], scripts, a) for a in g["partial"]]
        present = sorted({names[t]["script"] for t in g["supported"]} | {names[a["tag"]]["script"] for a in g["partial"]})
        regions = [(c, n) for c, n in REGIONS if any(c in names[t]["regions"] for t in g["supported"] + [a["tag"] for a in g["partial"]])]
        chips = lambda key, items: "".join(f"<button data-f='{key}:{v}'>{e(label)}</button>" for v, label in items)
        styles = g["styles"]
        shown = ", ".join(e(x) for x in styles[:6]) + (f" and {len(styles) - 6} more" if len(styles) > 6 else "")
        body += (
            f"<div class='lang-group'><h3>{shown}</h3>"
            f"<p><b>{len(g['supported'])}</b> languages supported, <b>{len(g['partial'])}</b> more with at least 40 % of their letters.</p>"
            "<div class='lfilters'>"
            f"<div><span>Show</span><button data-f='status:all' class='on'>All</button>{chips('status', (('ok', 'Supported'), ('miss', 'With missing letters'), ('near', 'Under 10 % short')))}</div>"
            + (f"<div><span>Script</span><button data-f='script:all' class='on'>All</button>{chips('script', [(s, scripts.get(s, s)) for s in present])}</div>" if len(present) > 1 else "")
            + (f"<div><span>Spoken in</span><button data-f='region:all' class='on'>All</button>{chips('region', regions)}</div>" if regions else "")
            + f"<div><span>Sort</span><button data-f='sort:coverage' class='on'>Coverage</button>{chips('sort', (('speakers', 'Speakers'), ('name', 'Name')))}</div>"
            "</div>"
            "<div class='lsum'><span class='lcount'></span>"
            "<span class='lunion'>Letters to add for the languages shown: <b class='lneed'>0</b> "
            "<button data-union='names'>Copy glyph names</button><button data-union='uni'>Copy Unicode values</button>"
            "<button data-union='chars'>Copy characters</button></span></div>"
            f"<div class='lrows'>{''.join(rows)}</div></div>")
    return (f"<section id='languages'><h2>Languages</h2><p class='muted'>A language counts as supported when the font has all of its "
            f"everyday letters, upper and lower case. The bar is the share of those letters. {e(langs['source'])}.</p>{body}{STYLE}{SCRIPT}</section>")


STYLE = """<style>
.lang-group{margin:0 0 28px}.lang-group h3{font-size:15px;margin:0 0 4px}.lang-group>p{margin:4px 0 10px;font-size:13px}
.lfilters{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}
.lfilters>div{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.lfilters span{width:78px;font-family:var(--mono);font-size:10.5px;color:var(--faint);text-transform:uppercase;letter-spacing:.06em}
.lang-group button{border:1px solid var(--line-2);background:var(--surface);border-radius:var(--r);padding:3px 9px;font-family:var(--mono);font-size:11px;color:var(--ink-2);cursor:pointer}
.lang-group button:hover{border-color:var(--accent)}.lang-group button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.lsum{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:0 0 8px;font-size:12.5px;color:var(--muted)}
.lunion button{margin-left:4px}
.lrows{border:1px solid var(--line);border-radius:var(--r);background:var(--surface);overflow:hidden}
.lrow{display:grid;grid-template-columns:minmax(150px,1.1fr) minmax(120px,2fr) 118px 96px;gap:10px;align-items:center;padding:7px 12px;border-top:1px solid var(--line);font-size:13px}
.lrow:first-child{border-top:0}.lrow small{color:var(--muted);font-family:var(--mono);font-size:10.5px}
.lrow .bar{height:7px;border-radius:4px;background:var(--sunken);overflow:hidden}.lrow .bar i{display:block;height:100%;background:var(--accent)}
.lrow.near .bar i{background:var(--warn)}.lrow.far .bar i{background:var(--faint)}
.lrow .lp{font-family:var(--mono);font-size:12px;text-align:right;white-space:nowrap}.lrow .lmiss{justify-self:end}
.ldet{grid-column:1/-1;padding:6px 0 4px}.ldet table{width:auto;min-width:60%}.lg{font-size:20px;line-height:1}
.lcopy{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
@media (max-width:640px){.lrow{grid-template-columns:1fr 100px}.lrow .bar{grid-column:1/-1;order:3}}
@media print{.lfilters,.lunion,.lcopy,.lmiss{display:none}.ldet{display:block!important}}
</style>"""

SCRIPT = """<script>(function(){
function copy(text,btn){
  var old=btn.textContent;
  function done(ok){btn.textContent=ok?"Copied":"Copy failed";setTimeout(function(){btn.textContent=old},1400)}
  function fallback(){var t=document.createElement("textarea");t.value=text;t.style.cssText="position:fixed;opacity:0";document.body.appendChild(t);t.select();
    var ok=false;try{ok=document.execCommand("copy")}catch(e){}document.body.removeChild(t);done(ok)}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){done(true)},fallback)}else fallback()
}
document.querySelectorAll(".lang-group").forEach(function(g){
  var st={status:"all",script:"all",region:"all",sort:"coverage"},box=g.querySelector(".lrows"),rows=[].slice.call(box.children);
  function apply(){
    var shown=0,need={},names={},chars={};
    rows.forEach(function(r){var p=+r.dataset.pct,ok=true;
      if(st.status==="ok")ok=p>=100;else if(st.status==="miss")ok=p<100;else if(st.status==="near")ok=p>=90&&p<100;
      if(ok&&st.script!=="all")ok=r.dataset.script===st.script;
      if(ok&&st.region!=="all")ok=(" "+r.dataset.regions+" ").indexOf(" "+st.region+" ")>=0;
      r.hidden=!ok;
      if(ok){shown++;var u=r.dataset.uni?r.dataset.uni.split(" "):[],n=r.dataset.names?r.dataset.names.split(" "):[],c=Array.from(r.dataset.chars||"");
        u.forEach(function(x,i){need[x]=1;names[x]=n[i];chars[x]=c[i]})}});
    var by={coverage:function(a,b){return b.dataset.pct-a.dataset.pct||b.dataset.speakers-a.dataset.speakers},
            speakers:function(a,b){return b.dataset.speakers-a.dataset.speakers},
            name:function(a,b){return a.dataset.name<b.dataset.name?-1:1}}[st.sort];
    rows.slice().sort(by).forEach(function(r){box.appendChild(r)});
    var keys=Object.keys(need).sort();g._union={uni:keys.join(" "),names:keys.map(function(k){return names[k]}).join(" "),chars:keys.map(function(k){return chars[k]}).join("")};
    g.querySelector(".lcount").textContent=shown+" of "+rows.length+" languages shown";
    g.querySelector(".lneed").textContent=keys.length;
  }
  g.addEventListener("click",function(e){var b=e.target.closest&&e.target.closest("button");if(!b)return;
    if(b.dataset.f){var k=b.dataset.f.split(":");st[k[0]]=k[1];
      [].forEach.call(g.querySelectorAll("[data-f^='"+k[0]+":']"),function(x){x.classList.toggle("on",x===b)});apply();return}
    if(b.classList.contains("lmiss")){var d=b.parentNode.querySelector(".ldet");d.hidden=!d.hidden;return}
    if(b.dataset.copy){var r=b.closest(".lrow");copy(r.dataset[b.dataset.copy],b);return}
    if(b.dataset.union){copy(g._union[b.dataset.union],b)}
  });
  apply();
});
})();</script>"""
