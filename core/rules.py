"""Rule cards: one Markdown file per check in rules/<check id>.md.

A card explains a check to people: what it checks, why it matters, how it is
measured, when it does not apply, how to fix it, an example and the sources.
The code keeps the logic; the card keeps the explanation. `validate` makes
sure the two agree (id, category, severity, action), and `render_page` builds
the Rules page from the cards.

The front matter is a small subset of YAML, parsed here so the browser build
needs no extra package:

    ---
    id: names.gdi_length
    title: ...
    sources:
      - Label | https://...
    ---
"""

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.normpath(os.path.join(HERE, "..", "rules"))
REPO_EDIT = "https://github.com/nnedashkovsky/fontqa/edit/main/rules/"
RULES_URL = "https://nnedashkovsky.github.io/fontqa/rules/"
# card sections only an engineer sees (core/levels.py)
ENGINEER_SECTIONS = {"How it is checked"}
SECTIONS = ("What it checks", "Why it matters", "How it is checked", "When it does not apply", "How to fix")
LIST_KEYS = ("sources",)


# ------------------------------------------------------------------ reading

def parse(text):
    """(meta dict, Markdown body) from a card."""
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        raise ValueError("no front matter")
    meta, key = {}, None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        item = re.match(r"\s+-\s+(.*)", line)
        if item and key:
            meta.setdefault(key, []).append(item.group(1).strip())
            continue
        k, _, v = line.partition(":")
        key = k.strip()
        meta[key] = v.strip() if v.strip() else []
    for k in ("related",):
        if isinstance(meta.get(k), str):
            meta[k] = [x.strip() for x in meta[k].split(",") if x.strip()]
    meta["sources"] = [tuple(x.strip() for x in s.split("|", 1)) if "|" in s else (s, "")
                       for s in meta.get("sources") or []]
    return meta, m.group(2).strip()


def load(folder=RULES_DIR):
    cards = {}
    if not os.path.isdir(folder):
        return cards
    for name in sorted(os.listdir(folder)):
        if name.endswith(".md"):
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                meta, body = parse(f.read())
            meta["body"], meta["file"] = body, name
            cards[meta.get("id") or name[:-3]] = meta
    return cards


def section(body, name):
    """The Markdown under '## name' up to the next '## '."""
    m = re.search(r"^## " + re.escape(name) + r"\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


_CACHE = {}


def for_issue(check_id, folder=RULES_DIR):
    """What a report needs from a card: why it matters and how it is checked (Markdown), or {}."""
    if folder not in _CACHE:
        try:
            _CACHE[folder] = load(folder)
        except Exception:  # a broken card must not break an inspection
            _CACHE[folder] = {}
    card = _CACHE[folder].get(check_id)
    if not card:
        return {}
    return {"why": section(card["body"], "Why it matters"), "how": section(card["body"], "How it is checked")}


def validate(cards, registry):
    """(errors, notes). Errors: a card and its check disagree, or a card has no check."""
    errors, notes = [], []
    checks = {c.id: c for c in registry}
    for cid, card in cards.items():
        if card["file"] != cid + ".md":
            errors.append(f"{card['file']}: id {cid} does not match the file name")
        c = checks.get(cid)
        if not c:
            errors.append(f"{card['file']}: no check with id {cid}")
            continue
        if card.get("level") and card["level"] != c.level:
            errors.append(f"{cid}: level is {card['level']!r} in the card, {c.level!r} in the code")
        for k in ("category", "severity", "action"):
            if str(card.get(k)) != str(getattr(c, k)):
                errors.append(f"{cid}: {k} is {card.get(k)!r} in the card, {getattr(c, k)!r} in the code")
        heads = re.findall(r"^## (.+)$", card["body"], re.M)
        missing = [s for s in SECTIONS if s not in heads]
        if missing:
            errors.append(f"{cid}: missing sections: {', '.join(missing)}")
        for r in card.get("related") or []:
            if r not in checks:
                errors.append(f"{cid}: related {r} is not a check")
        if card.get("title") != c.title:
            notes.append(f"{cid}: title differs from the code ({c.title!r})")
    without = sorted(set(checks) - set(cards))
    if without:
        errors.append(f"{len(without)} checks have no card: {', '.join(without)}")
    return errors, notes


# ------------------------------------------------------------------ Markdown

def _inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def markdown(text):
    """Headings, paragraphs, lists, tables and inline code/bold/italic/links — what cards use."""
    out, para, lst, table = [], [], None, []

    def flush():
        nonlocal para, lst, table
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + f"</{tag}>")
            lst = None
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
            body = [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            t = "<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in rows[0]) + "</tr></thead>"
            t += "<tbody>" + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody>"
            out.append(f'<div class="tw"><table>{t}</table></div>')
            table = []

    for line in text.splitlines():
        s = line.strip()
        h = re.match(r"(#{2,4})\s+(.*)", s)
        ul = re.match(r"[-*]\s+(.*)", s)
        ol = re.match(r"\d+\.\s+(.*)", s)
        if not s:
            flush()
        elif h:
            flush()
            n = len(h.group(1)) + 1
            out.append(f"<h{n}>{_inline(h.group(2))}</h{n}>")
        elif s.startswith("|"):
            if para or lst:
                flush()
            table.append(s)
        elif ul or ol:
            tag = "ul" if ul else "ol"
            if para or table or (lst and lst[0] != tag):
                flush()
            lst = lst or (tag, [])
            lst[1].append((ul or ol).group(1))
        elif lst and line.startswith(("  ", "\t")):
            lst[1][-1] += " " + s
        else:
            if lst or table:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


# ------------------------------------------------------------------ page

def by_level(body):
    """Card body as HTML, each '## ' section wrapped in a div with its level class."""
    out = []
    for m in re.finditer(r"^## (.+?)\s*$(.*?)(?=^## |\Z)", body, re.M | re.S):
        name, text = m.group(1).strip(), m.group(2)
        out.append(f'<div class="sec{" l3" if name in ENGINEER_SECTIONS else ""}">' + markdown("## " + name + "\n" + text) + "</div>")
    return "\n".join(out)


def render_page(cards, registry, tool_url="../web/"):
    from . import levels
    from .checks import CATEGORIES
    from .report_html import HEAD as REPORT_HEAD
    e = html.escape
    checks = {c.id: c for c in registry}
    order = sorted(checks.values(), key=lambda c: (c.category, c.id))
    nav, body = [], []
    for cat, label in CATEGORIES.items():
        group = [c for c in order if c.category == cat]
        if not group:
            continue
        nav.append(f'<div class="ncat">{cat} · {e(label)}</div>')
        body.append(f'<h2 class="cat" id="cat-{cat}">{cat} · {e(label)}</h2>')
        for c in group:
            card = cards.get(c.id)
            title = card.get("title") if card else c.title
            cls = " ".join(x for x in ("" if card else "draft", "l3" if c.level == "engineer" else "") if x)
            nav.append(f'<a href="#{e(c.id)}" class="{cls}">{e(title)}</a>')
            body.append(_rule(c, card, checks))
    head = levels.head(REPORT_HEAD.replace("{{title}} — inspection", "Rules — Font QA").replace("</head>", EXTRA_CSS + "</head>"))
    done = sum(1 for c in checks if c in cards)
    return (head + f"""<div class="wrap">
<header><div><div class="kicker">Font QA</div><h1>Rules</h1>
<div class="sub">{len(checks)} checks · {sum(1 for c in checks.values() if c.level == "designer")} at the Designer level · {done} explained in full · <a href="{e(tool_url)}">open the tool</a></div></div>
<div class="ctl">{levels.SWITCH}<button class="theme" id="theme">auto</button></div></header>{levels.panel()}
<div class="filters"><input id="q" type="search" placeholder="Search rules: name ID 1, fsSelection, Word…"></div>
<div class="layout"><nav>{''.join(nav)}</nav><main>{''.join(body)}</main></div>
</div>""" + PAGE_SCRIPT + levels.SCRIPT + "</body></html>")


def _badges(c):
    from .report_html import ACTION_LABEL
    return (f'<span class="tag {c.action}">{ACTION_LABEL.get(c.action, c.action)}</span>'
            f'<span class="tag sev-{c.severity}">{c.severity}</span>'
            f'<span class="tag lv">{"Designer + Engineer" if c.level == "designer" else "Engineer"}</span>'
            f'<span class="cls">{c.category} · {c.scope}</span>')


def _rule(c, card, checks):
    e = html.escape
    rid = e(c.id)
    lvl = " l3" if c.level == "engineer" else ""
    if not card:
        sym = "".join(f"<li>{e(s)}</li>" for s in c.symptoms)
        return f"""<article class="rule draft{lvl}" id="{rid}" data-search="{e((c.id + ' ' + c.title + ' ' + c.what + ' ' + c.basis).lower())}">
<div class="ih"><code>{rid}</code>{_badges(c)}<span class="cls">short description, full card not written yet</span></div>
<h3>{e(c.title)}</h3><p class="lead">{e(c.what[:1].upper() + c.what[1:])}.</p>
<p><b>Why:</b> {e(c.basis)}</p><p><b>Fix:</b> {e(c.fix)}</p>{f'<p><b>Users may see:</b></p><ul>{sym}</ul>' if sym else ''}
</article>"""
    srcs = "".join(f'<li><a href="{e(u)}">{e(t)}</a></li>' if u else f"<li>{e(t)}</li>" for t, u in card["sources"])
    rel = " ".join(f'<a href="#{e(r)}"><code>{e(r)}</code></a>' for r in card.get("related") or [] if r in checks)
    text = " ".join([c.id, card.get("title", ""), card.get("summary", ""), card["body"]]).lower()
    return f"""<article class="rule{lvl}" id="{rid}" data-search="{e(text)}">
<div class="ih"><code>{rid}</code>{_badges(c)}<a class="edit" href="{REPO_EDIT}{e(card['file'])}">Edit this rule</a></div>
<h3>{e(card.get('title', c.title))}</h3>
<p class="lead">{_inline(card.get('summary', ''))}</p>
<p class="applies"><b>Applies to:</b> {_inline(card.get('applies', ''))}</p>
<div class="md">{by_level(card['body'])}</div>
{f'<div class="l3"><h4>Sources</h4><ul class="src">{srcs}</ul></div>' if srcs else ''}
{f'<p class="rel"><b>Related:</b> {rel}</p>' if rel else ''}
</article>"""


EXTRA_CSS = """<style>
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:28px;margin-top:6px}main{min-width:0}
nav{position:sticky;top:12px;align-self:start;max-height:calc(100vh - 24px);overflow:auto;font-size:12.5px;padding-right:6px}
nav a{display:block;color:var(--ink-2);text-decoration:none;padding:3px 0;line-height:1.3}nav a:hover{color:var(--accent)}
nav a.draft{color:var(--faint)}
.ncat{font-size:10.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin:14px 0 4px}
.ncat:first-child{margin-top:0}
h2.cat{margin:30px 0 12px}h2.cat:first-child{margin-top:0}
.rule{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:18px 22px;margin-bottom:14px;scroll-margin-top:12px;max-width:820px}
.rule.draft{background:var(--surface-2)}
.rule h3{font-size:19px;font-weight:600;margin:8px 0 6px;text-wrap:balance}
.rule .lead{font-size:15px;color:var(--ink-2);margin:0 0 6px}
.rule .applies{font-size:12.5px;color:var(--muted);margin:0 0 4px}
.md h3{font-size:10.5px;font-weight:600;letter-spacing:.11em;text-transform:uppercase;color:var(--faint);margin:22px 0 6px}
.md p,.md li{font-size:14px;line-height:1.6;max-width:72ch}.md ul,.md ol{padding-left:22px}.md li{margin:3px 0}
.rule h4{font-size:10.5px;font-weight:600;letter-spacing:.11em;text-transform:uppercase;color:var(--faint);margin:22px 0 6px}
.src{font-size:12.5px;padding-left:18px}.rel{font-size:12.5px}
.tw{overflow-x:auto;margin:8px 0}.tw table{width:auto;min-width:60%}
.tw th{text-align:left;font-size:11px;font-weight:600;color:var(--muted);padding:6px 12px 6px 0;border-bottom:1px solid var(--line)}
.tw td{font-size:13px;padding:6px 12px 6px 0;border-top:1px solid var(--line);vertical-align:top}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tag.lv{border:1px solid var(--line-2);color:var(--muted);font-family:var(--mono)}
.edit{margin-left:auto;font-family:var(--sans);font-size:12px}
code{font-size:12px;word-break:normal}
@media (max-width:860px){.layout{grid-template-columns:1fr}nav{display:none}.rule{padding:14px 16px}}
</style>"""

PAGE_SCRIPT = """<script>
(function(){
  var THEMES=["auto","light","dark"],t="auto";
  try{t=localStorage.getItem("fontqa:theme")||"auto"}catch(e){}
  function apply(x){if(x==="auto")delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=x;document.getElementById("theme").textContent=x}
  apply(t);
  document.getElementById("theme").onclick=function(){t=THEMES[(THEMES.indexOf(t)+1)%3];apply(t);try{localStorage.setItem("fontqa:theme",t)}catch(e){}};
  var q=document.getElementById("q");
  function filter(){var s=q.value.toLowerCase().trim();
    document.querySelectorAll(".rule").forEach(function(el){el.hidden=s&&el.dataset.search.indexOf(s)<0});
    document.querySelectorAll("h2.cat").forEach(function(h){var n=h.nextElementSibling,any=false;h.hidden=false;
      while(n&&!n.matches("h2.cat")){if(!n.hidden&&getComputedStyle(n).display!=="none")any=true;n=n.nextElementSibling}h.hidden=!any});
    document.querySelectorAll(".ncat").forEach(function(h){var n=h.nextElementSibling,any=false;
      while(n&&!n.matches(".ncat")){if(getComputedStyle(n).display!=="none")any=true;n=n.nextElementSibling}h.style.display=any?"":"none"});}
  q.oninput=filter;window.onLevel=filter;filter();
})();
</script>"""
