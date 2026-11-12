"""Attachments next to the report: glyph grid, GSUB listing, proofs, specimen.

RT delivered the same three kinds of material without judgements: an all-code
glyph comparison with four reference fonts, a GSUB substitution listing, and
the visual inspection. Theirs were PDFs of 110 MB each because every page
embedded the complete fonts. Here every font is subset to the characters the
page shows and embedded once as WOFF2, so a Latin grid is a few hundred KB,
and the pages print to PDF from the browser (A4 landscape for the grid).

The grid adds what RT left out: a hint where a glyph departs from the
references more than the rest of the font does. The font's own relation to the
references (heavier, wider) is taken as its median, and a glyph is marked only
when its ratio is far from that median (robust z-score) — a pointer for the
eye, not a verdict.
"""

import base64
import html
import io
import math
import statistics
import unicodedata

import logging

from fontTools import subset
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools import unicodedata as ucd

from .report_html import HEAD

e = lambda s: html.escape("" if s is None else str(s))

EXTRA_CSS = """<style>
.cells{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:6px}
.cell{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:4px 6px}
.cell.hint{border-color:var(--warn);box-shadow:inset 0 0 0 1px var(--warn)}
.cell .cp{font-family:var(--mono);font-size:9.5px;color:var(--faint);display:flex;justify-content:space-between}
.cell .cp b{color:var(--warn);font-weight:600}
.cell .gl{display:grid;grid-template-columns:repeat(var(--n),1fr);align-items:end;height:46px}
.cell .gl span{font-size:30px;line-height:46px;text-align:center;overflow:hidden;white-space:pre}
.cell .gl span.t{background:var(--accent-soft);border-radius:4px}
.cell .gl span.miss{border:1px dotted var(--line-2);height:30px;margin:8px 4px;border-radius:3px}
.block{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:16px 0 6px}
.legend-row{display:flex;gap:14px;flex-wrap:wrap;font-family:var(--mono);font-size:11px;color:var(--muted);margin:8px 0}
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}
.toolbar button{border:1px solid var(--line-2);background:var(--surface);border-radius:var(--r);padding:4px 10px;font-family:var(--mono);font-size:11.5px;color:var(--ink-2);cursor:pointer}
.toolbar button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
table.gsub td,table.gsub th{padding:4px 8px;border-top:1px solid var(--line);font-size:12px;vertical-align:middle;text-align:left}
table.gsub svg{height:34px;width:auto;vertical-align:middle;fill:var(--ink)}
table.gsub .live{font-size:26px;white-space:nowrap}
.mono{font-family:var(--mono);font-size:11px}
.proof{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:12px 14px;margin-bottom:14px}
.proof h3{font-size:13px;margin:0 0 8px;font-family:var(--mono)}
.proof .wf div{white-space:nowrap;overflow:hidden;text-overflow:clip;line-height:1.25}
.proof .wf small{font-family:var(--mono);font-size:9px;color:var(--faint);display:inline-block;width:34px}
.proof .lines div{font-size:22px;line-height:1.35;overflow-wrap:anywhere}
@media print{@page{size:A4 landscape;margin:10mm}.toolbar{display:none}.cell{break-inside:avoid}}
</style>"""

SAMPLE = "Hamburgefonstiv 0123456789 ÀÉÎõüß"
SPACING = ["HHOHHOOHOOHH nnonnoonoonn", "HOHAHBHCHDHEHFHGHHHIHJHKHLHMHNHOHPHQHRHSHTHUHVHWHXHYHZH",
           "nonanbncndnenfngnhninjnknlnmnnnonpnqnrnsntnunvnwnxnynzn", "H0H1H2H3H4H5H6H7H8H9H n0n1n2n3n4n5n6n7n8n9n"]
KERNING = ["AVATAR Tofu Wave Yolk LATTE", "Ta Te To Tr Tu Tw Ty Va Ve Vo Wa We Wo Ya Ye Yo", "“Quoted.” ‘Said,’ (Paren) [Bracket] {Brace}",
           "L’ T. V, W. Y; F. P, r. y, f) j] 7/ 1/2"]


# ------------------------------------------------------------------ fonts

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def subset_b64(path, codepoints, keep_layout=True):
    """WOFF2 of the font cut down to `codepoints` (base64), or None when nothing is left."""
    font = TTFont(path)
    opts = subset.Options()
    opts.layout_features = ["*"] if keep_layout else []
    opts.flavor = "woff2"
    opts.notdef_outline = True
    opts.name_IDs = ["*"]
    opts.drop_tables += ["DSIG"]
    sub = subset.Subsetter(opts)
    cmap = font.getBestCmap() or {}
    cps = [c for c in codepoints if c in cmap]
    if not cps:
        return None
    sub.populate(unicodes=cps)
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def face_css(name, b64):
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def pick_styles(views):
    """Grid styles: per family and slope, every style at the weight closest to 400 (statics, one copy each).

    A family can give Regular, Dark, Display, Dark Display (upright and italic); Squishy Blob gives
    both its styles, Dark and Outline, which share weight 400.
    """
    from .checks.lineage import style_key
    groups = {}
    for v in views:
        if not v.ok or v.variable or not v.fmt:
            continue
        fam = (v.names.get("16") or v.family).strip()
        if len(fam) <= 1 or not fam.isprintable():
            continue  # obfuscated web names: the same style exists in another lineage
        groups.setdefault((fam, v.italic), []).append(v)
    out, seen = [], set()
    for key in sorted(groups):
        vs = groups[key]
        target = min(abs((v.style.get("weight_class") or 400) - 400) for v in vs)
        for v in sorted(vs, key=lambda x: (not x.is_sfnt, x.lineage != "Desktop", x.rel)):
            k = style_key(v.rel)
            if abs((v.style.get("weight_class") or 400) - 400) == target and k not in seen:
                seen.add(k)
                out.append(v)
    return out


def _metrics(path):
    """codepoint -> (area, width, upm) for every mapped glyph; area of the ink, not of the box."""
    font = TTFont(path, lazy=True)
    gs = font.getGlyphSet()
    upm = font["head"].unitsPerEm
    out = {}
    for cp, g in (font.getBestCmap() or {}).items():
        try:
            pen = AreaPen(gs)
            gs[g].draw(pen)
            out[cp] = (abs(pen.value) / upm / upm, gs[g].width / upm)
        except Exception:
            continue
    return out


def _robust_flags(ratios, z=3.5):
    """Codepoints whose log ratio is far from the font's own median (median absolute deviation)."""
    vals = [math.log(r) for r in ratios.values() if r > 0]
    if len(vals) < 20:
        return {}
    med = statistics.median(vals)
    mad = statistics.median(abs(x - med) for x in vals) or 1e-6
    out = {}
    for cp, r in ratios.items():
        if r > 0:
            score = 0.6745 * (math.log(r) - med) / mad
            if abs(score) >= z:
                out[cp] = score
    return out


# ------------------------------------------------------------------ glyph grid

def glyph_grid(target, refs, title):
    """All mapped characters of `target` (a FontView) beside the reference fonts.

    `refs` are (label, path) for the references that match the target's slope.
    """
    tcmap = sorted(c for c in target.cmap if c > 0x20 and unicodedata.category(chr(c)) not in ("Cc", "Cf", "Zs"))
    faces = [face_css("T", subset_b64(target.path, tcmap))]
    ref_cmaps = []
    for k, (label, path) in enumerate(refs):
        b64 = subset_b64(path, tcmap, keep_layout=False)
        if b64:
            faces.append(face_css(f"R{k}", b64))
        ref_cmaps.append(set((TTFont(path, lazy=True).getBestCmap() or {})))
    # hints: departures from the references beyond the font's own typical relation to them
    tm = _metrics(target.path)
    rms = [_metrics(p) for _, p in refs]
    area_r, width_r = {}, {}
    for cp in tcmap:
        ra = [m[cp][0] for m in rms if cp in m and m[cp][0] > 0]
        rw = [m[cp][1] for m in rms if cp in m and m[cp][1] > 0]
        if cp in tm and ra and tm[cp][0] > 0:
            area_r[cp] = tm[cp][0] / statistics.median(ra)
        if cp in tm and rw and tm[cp][1] > 0:
            width_r[cp] = tm[cp][1] / statistics.median(rw)
    heavy, wide = _robust_flags(area_r), _robust_flags(width_r)
    n = 1 + len(refs)
    blocks, cur = [], None
    cells = []
    for cp in tcmap:
        block = ucd.block(chr(cp))
        if block != cur:
            if cells:
                blocks.append((cur, cells))
            cur, cells = block, []
        hint = []
        if cp in heavy:
            hint.append("mass " + ("+" if heavy[cp] > 0 else "−"))
        if cp in wide:
            hint.append("width " + ("+" if wide[cp] > 0 else "−"))
        ch = e(chr(cp))
        spans = [f"<span class='t' style=\"font-family:'T'\">{ch}</span>"]
        for k in range(len(refs)):
            spans.append(f"<span style=\"font-family:'R{k}'\">{ch}</span>" if cp in ref_cmaps[k] else "<span class='miss'></span>")
        cells.append(f"<div class='cell{' hint' if hint else ''}' data-hint='{1 if hint else 0}'><div class='cp'><span>U+{cp:04X}</span>"
                     f"<b>{e(' · '.join(hint))}</b></div><div class='gl' style='--n:{n}'>{''.join(spans)}</div></div>")
    if cells:
        blocks.append((cur, cells))
    flagged = sum(1 for cp in tcmap if cp in heavy or cp in wide)
    legend = " · ".join([f"T {e(target.label())}"] + [f"R{k + 1} {e(lab)}" for k, (lab, _) in enumerate(refs)])
    body = "".join(f"<div class='block'>{e(b)}</div><div class='cells'>{''.join(cs)}</div>" for b, cs in blocks)
    return _page(title, f"""
<header><div><div class="kicker">Glyph comparison</div><h1>{e(target.label())}</h1>
<div class="sub">{e(target.rel)} · {len(tcmap)} characters · references matched by slope</div></div></header>
<p class="muted">Every mapped character of the font (T, shaded) beside the reference fonts. A dotted box means the reference has no
such character; it is not drawn by a fallback font. Glyphs are shown with default features only.
<b>Marked cells</b> differ from the references in ink mass or advance width far more than this font does on average
(robust z-score ≥ 3.5 of the log ratio) — a pointer for the eye, not a judgement. {flagged} of {len(tcmap)} are marked.</p>
<div class="legend-row">{legend}</div>
<div class="toolbar"><button id="only">Show marked only</button><button onclick="window.print()">Print / PDF</button></div>
{body}
<script>document.getElementById('only').onclick=function(){{this.classList.toggle('on');var on=this.classList.contains('on');
document.querySelectorAll('.cell').forEach(function(c){{c.hidden=on&&c.dataset.hint!=='1'}});
document.querySelectorAll('.cells').forEach(function(g){{var v=[].some.call(g.children,function(c){{return !c.hidden}});
g.hidden=!v;g.previousElementSibling.hidden=!v}});}};</script>""", faces)


# ------------------------------------------------------------------ GSUB listing

def _svg(font, gs, name, upm, asc, desc):
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    w = max(gs[name].width, 1)
    return (f"<svg viewBox='0 {-asc} {w} {asc - desc}' preserveAspectRatio='xMinYMid meet'>"
            f"<path transform='scale(1,-1)' d='{pen.getCommands()}'/></svg>")


def gsub_listing(views, title):
    """Every substitution of every GSUB feature: input → output, with outlines and live rendering."""
    sections, faces = [], []
    for k, v in enumerate(views):
        font = TTFont(v.path)
        if "GSUB" not in font:
            continue
        gs = font.getGlyphSet()
        upm = font["head"].unitsPerEm
        asc, desc = font["hhea"].ascent, font["hhea"].descent
        rev = {}
        for cp, g in sorted((font.getBestCmap() or {}).items()):
            rev.setdefault(g, cp)
        b64 = subset_b64(v.path, sorted(rev.values()))
        faces.append(face_css(f"F{k}", b64))
        order = {g: i for i, g in enumerate(font.getGlyphOrder())}
        table = font["GSUB"].table
        lookups = table.LookupList.Lookup if table.LookupList else []
        summary, rows, count = [], [], 0
        for fr in (table.FeatureList.FeatureRecord if table.FeatureList else []):
            tag = fr.FeatureTag
            for li in fr.Feature.LookupListIndex:
                lk = lookups[li]
                n_in_lookup = 0
                for st in lk.SubTable:
                    ltype = lk.LookupType
                    if ltype == 7:
                        ltype, st = st.ExtensionLookupType, st.ExtSubTable
                    pairs = []
                    if ltype == 1:
                        pairs = [([a], [b]) for a, b in st.mapping.items()]
                    elif ltype == 3:
                        pairs = [([a], alts) for a, alts in st.alternates.items()]
                    elif ltype == 4:
                        pairs = [([first] + lig.Component, [lig.LigGlyph]) for first, ligs in st.ligatures.items() for lig in ligs]
                    elif ltype == 2:
                        pairs = [([a], seq) for a, seq in st.mapping.items()]
                    else:
                        rows.append(f"<tr><td>{e(tag)}</td><td>{li} · type {ltype}</td><td colspan='3' class='muted'>contextual or chaining rule — "
                                    f"see the feature code</td></tr>")
                        continue
                    for ins, outs in pairs:
                        count += 1
                        n_in_lookup += 1
                        live = ""
                        text = "".join(chr(rev[g]) for g in ins if g in rev)
                        if len(text) == len(ins):
                            live = (f"<span class='live' style=\"font-family:'F{k}';font-feature-settings:'{tag}' 0\">{e(text)}</span> → "
                                    f"<span class='live' style=\"font-family:'F{k}';font-feature-settings:'{tag}' 1\">{e(text)}</span>")
                        lab = lambda g: f"{order.get(g, '?')} {g}" + (f" U+{rev[g]:04X}" if g in rev else "")
                        rows.append(f"<tr><td>{e(tag)}</td><td>{li} · type {ltype}</td>"
                                    f"<td>{''.join(_svg(font, gs, g, upm, asc, desc) for g in ins)}<div class='mono'>{e(' + '.join(lab(g) for g in ins))}</div></td>"
                                    f"<td>{''.join(_svg(font, gs, g, upm, asc, desc) for g in outs[:8])}<div class='mono'>{e(' | '.join(lab(g) for g in outs[:8]))}"
                                    f"{' …' if len(outs) > 8 else ''}</div></td><td>{live}</td></tr>")
                summary.append((tag, li, lk.LookupType, n_in_lookup))
        gpos = _gpos_summary(font)
        sections.append(f"""<section><h2>{e(v.label())} <span class="count">{e(v.rel)}</span></h2>
<p class="muted">{len(font.getGlyphOrder())} glyphs · {count} substitutions · GPOS: {e(gpos)}</p>
<div class="scroll"><table class="data"><tr><th>Feature</th><th>Lookup</th><th>Type</th><th>Substitutions</th></tr>
{''.join(f'<tr><td>{e(t)}</td><td>{li}</td><td>{ty}</td><td>{n}</td></tr>' for t, li, ty, n in summary)}</table></div>
<div class="scroll" style="margin-top:10px"><table class="gsub"><tr><th>Feature</th><th>Lookup</th><th>Input</th><th>Output</th><th>Browser (off → on)</th></tr>
{''.join(rows)}</table></div></section>""")
    return _page(title, f"""<header><div><div class="kicker">GSUB listing</div><h1>{e(title)}</h1>
<div class="sub">feature → lookup → subtable → input, in table order · outlines from the fonts · live rendering in this browser</div></div></header>
<div class="toolbar"><button onclick="window.print()">Print / PDF</button></div>{''.join(sections)}""", faces)


def _gpos_summary(font):
    if "GPOS" not in font:
        return "none"
    t = font["GPOS"].table
    feats = sorted({fr.FeatureTag for fr in (t.FeatureList.FeatureRecord if t.FeatureList else [])})
    pairs, classes, marks = 0, 0, 0
    for lk in (t.LookupList.Lookup if t.LookupList else []):
        for st in lk.SubTable:
            ltype = lk.LookupType
            if ltype == 9:
                ltype, st = st.ExtensionLookupType, st.ExtSubTable
            if ltype == 2 and st.Format == 1:
                pairs += sum(len(ps.PairValueRecord) for ps in st.PairSet)
            elif ltype == 2:
                classes += st.Class1Count * st.Class2Count
            elif ltype in (4, 5, 6):
                marks += len(st.MarkCoverage.glyphs) if hasattr(st, "MarkCoverage") else len(st.Mark1Coverage.glyphs)
    return f"features {', '.join(feats)}; {pairs} glyph pairs, {classes} class cells; {marks} mark entries"


# ------------------------------------------------------------------ proofs and specimen

def proofs(views, title):
    """Waterfall, spacing and kerning strings for every picked style."""
    faces, blocks = [], []
    text = SAMPLE + " " + " ".join(SPACING + KERNING)
    cps = sorted({ord(c) for c in text if c != " "})
    for k, v in enumerate(views):
        b64 = subset_b64(v.path, cps)
        if not b64:
            continue
        faces.append(face_css(f"P{k}", b64))
        wf = "".join(f"<div style=\"font-size:{s}px\"><small>{s}</small>{e(SAMPLE)}</div>" for s in (9, 11, 14, 18, 24, 36, 48, 72))
        lines = "".join(f"<div>{e(t)}</div>" for t in SPACING + KERNING)
        blocks.append(f"<div class='proof' style=\"font-family:'P{k}'\"><h3 style='font-family:var(--mono)'>{e(v.label())} · {e(v.rel)}</h3>"
                      f"<div class='wf'>{wf}</div><div class='lines' style='margin-top:10px'>{lines}</div></div>")
    return _page(title, f"""<header><div><div class="kicker">Proofs</div><h1>{e(title)}</h1>
<div class="sub">waterfall, spacing strings (HOH / non) and kerning strings · default features</div></div></header>
<div class="toolbar"><button onclick="window.print()">Print / PDF</button></div>{''.join(blocks)}""", faces)


def specimen_section(views):
    """Report section: every style of the delivery in one line, fonts subset to the sample."""
    from .checks.lineage import style_key
    cps = sorted({ord(c) for c in SAMPLE if c != " "})
    seen, faces, rows = set(), [], []
    for v in sorted(views, key=lambda x: (x.lineage != "Desktop", not x.is_sfnt, x.rel)):
        if not v.ok or v.variable:
            continue
        key = style_key(v.rel)
        if key in seen:
            continue
        seen.add(key)
        b64 = subset_b64(v.path, cps)
        if not b64:
            continue
        name = f"S{len(faces)}"
        faces.append(face_css(name, b64))
        rows.append(f"<div class='spec'><div class='mono muted'>{e(v.label())} · {e(v.rel)}</div>"
                    f"<div style=\"font-family:'{name}';font-size:30px;line-height:1.25;white-space:nowrap;overflow:hidden\">{e(SAMPLE)}</div></div>")
    if not rows:
        return ""
    return (f"<style>{''.join(faces)}.spec{{padding:6px 0;border-top:1px solid var(--line)}}</style>"
            f"<section><h2>Specimen <span class='count'>{len(rows)}</span></h2><p class='muted'>Every static style once "
            f"(the Desktop copy where there is one), drawn from the delivered files.</p>{''.join(rows)}</section>")


def _page(title, body, faces):
    return (HEAD.replace("{{title}}", e(title)) + EXTRA_CSS + "<style>" + "".join(f for f in faces if f) + "</style>"
            + "<div class='wrap'>" + body + "</div></body></html>")


REF_DIR = None  # set by callers; default: $FONTQA_REFS


def default_refs(extra=()):
    """(upright, italic) reference lists: PT Sans/Serif Expert plus the user's own fonts."""
    import os
    d = REF_DIR or os.environ.get("FONTQA_REFS") or os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "CHECKER", "PT-EXPERT_FONTS"))
    up = [("PT Sans Expert", os.path.join(d, "PT-Sans-Expert_Regular.woff")),
          ("PT Serif Expert", os.path.join(d, "PT-Serif-Expert_Regular.woff"))]
    it = [("PT Sans Expert Italic", os.path.join(d, "PT-Sans-Expert_Italic.woff")),
          ("PT Serif Expert Italic", os.path.join(d, "PT-Serif-Expert_Italic.woff"))]
    up = [r for r in up if os.path.exists(r[1])]
    it = [r for r in it if os.path.exists(r[1])]
    for label, path in extra:
        up.append((label, path))
        it.append((label, path))
    return up, it


def views_for(paths, facts=None):
    from . import inventory
    from .fontview import FontView
    facts = facts or inventory.facts_for(paths)
    inv = inventory.build([dict(f) for f in facts])
    by = {f["path"]: f for f in inv["files"]}
    return [FontView(p, by[r]) for p, r in paths if r in by]


def build(views, refs_upright, refs_italic, title):
    """{file name: html} for every attachment."""
    out = {}
    styles = pick_styles(views)
    for v in styles:
        refs = refs_italic if v.italic else refs_upright
        name = "glyphs-" + "".join(ch if ch.isalnum() else "-" for ch in v.label()).strip("-").lower() + ".html"
        out[name] = glyph_grid(v, refs, f"{v.label()} — glyph comparison")
    if styles:
        out["gsub.html"] = gsub_listing(styles, title)
        out["proofs.html"] = proofs(styles, title)
    return out


# ------------------------------------------------------------------ menus and checklist

def menus_page(result):
    """Predicted menus per install group, and the manual checklist for every predicted symptom.

    The checklist keeps its state (observed / not observed, a note, a screenshot) in the
    browser, and exports it as JSON, so a person can do RT's install-and-look round on a
    real Windows and Mac and hand the result back.
    """
    import json as _json
    from .menus import LANGS
    sim = result.get("menus") or []
    if isinstance(sim, dict):
        sim = []

    def ul(items, extra=lambda it: ""):
        return "<ul class='menu'>" + "".join(
            f"<li><b>{e(it['family'])}</b>{extra(it)}<div class='st'>{e(' · '.join(it['styles']))}</div></li>" for it in items) + "</ul>"

    groups = []
    for g in sim:
        mac = "".join(f"<div class='col'><h4>macOS · {e(LANGS.get(lang, lang))} · Font Book</h4>"
                      + ul(fb, lambda it: f" <span class='bad'>{it['lost']} hidden</span>" if it["lost"] else "") + "</div>"
                      for lang, fb in g.get("fontbook", {}).items())
        vf = "".join(f"<div class='col'><h4>macOS · variable font</h4><ul class='menu'><li><b>{e(v['family'])}</b>"
                     f"<div class='st'>{e(' · '.join(v['shown']))}</div>"
                     + (f"<div class='bad'>twice: {e(', '.join(v['duplicates']))}</div>" if v["duplicates"] else "")
                     + (f"<div class='bad'>missing: {e(', '.join(v['missing']))}</div>" if v["missing"] else "")
                     + "</li></ul></div>" for v in g.get("macos_vf", []))
        groups.append(f"""<section><h2>{e(g['group'])}</h2><div class='cols3'>
<div class='col'><h4>Windows · Word, Notepad (GDI)</h4>{ul(g['gdi'], lambda it: (" <span class='bad'>cut at 31</span>" if it['truncated'] else "") + (f" <span class='bad'>{it['lost']} lost</span>" if it['lost'] else ""))}</div>
<div class='col'><h4>Windows 11 · font dialog (WWS)</h4>{ul(g['wws'])}</div>{mac}{vf}</div></section>""")
    rows = "".join(f"""<tr data-id="{e(s['id'])}"><td>{e(s['id'])}</td><td>{e(s['environment'])}</td><td>{e(s['symptom'])}</td>
<td>{e(s['parent'])}</td><td><select><option value="">predicted</option><option value="observed">observed</option>
<option value="not observed">not observed</option><option value="n/a">not tested</option></select></td>
<td><input type="text" placeholder="note"><label class="shot">screenshot<input type="file" accept="image/*" hidden></label><img hidden></td></tr>"""
                   for s in result.get("symptoms", []))
    key = "fontqa:checklist:" + (result.get("title") or "") + ":" + (result.get("date") or "")
    return _page(f"{result.get('title')} — menus and checklist", f"""
<header><div><div class="kicker">Menus and checklist</div><h1>{e(result.get('title') or 'Fonts')}</h1>
<div class="sub">predicted from the name, OS/2 and fvar tables · {len(result.get('symptoms', []))} symptoms to confirm</div></div></header>
<p class="muted">How the fonts would appear in font menus, computed from the tables before anything is installed. Then the
checklist: install the fonts, look, and mark each predicted symptom; notes and screenshots stay in this browser and go into
the exported JSON.</p>
{''.join(groups) or '<p class="muted">No installable fonts.</p>'}
<section><h2>Checklist</h2><div class="toolbar"><button id="export">Export checklist JSON</button><button onclick="window.print()">Print / PDF</button></div>
<div class="scroll"><table class="data check"><tr><th>No.</th><th>Environment</th><th>Predicted symptom</th><th>Issue</th><th>Status</th><th>Evidence</th></tr>{rows}</table></div></section>
<style>.cols3{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.col{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:10px 12px}}
.col h4{{margin:0 0 6px;font-size:11px;font-family:var(--mono);color:var(--muted);font-weight:500}}
.menu{{list-style:none;margin:0;padding:0}}.menu li{{padding:4px 0;border-top:1px solid var(--line);font-size:12.5px}}
.menu li:first-child{{border-top:0}}.menu .st{{font-family:var(--mono);font-size:10.5px;color:var(--muted)}}
.bad{{color:var(--warn);font-family:var(--mono);font-size:10.5px}}
table.check input[type=text]{{width:100%;font:inherit;font-size:12px;border:1px solid var(--line-2);border-radius:5px;padding:2px 6px;background:var(--surface-2);color:var(--ink)}}
table.check select{{font-size:12px}}.shot{{font-family:var(--mono);font-size:10.5px;color:var(--accent);cursor:pointer}}
table.check img{{max-width:220px;display:block;margin-top:4px;border:1px solid var(--line);border-radius:4px}}</style>
<script>(function(){{var KEY={_json.dumps(key)},st={{}};try{{st=JSON.parse(localStorage.getItem(KEY)||localStorage.getItem(KEY.replace("fontqa:","trolcheck:"))||"{{}}")}}catch(e){{}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}}}
document.querySelectorAll("tr[data-id]").forEach(function(tr){{var id=tr.dataset.id,s=st[id]||{{}},sel=tr.querySelector("select"),
txt=tr.querySelector("input[type=text]"),file=tr.querySelector("input[type=file]"),img=tr.querySelector("img");
sel.value=s.status||"";txt.value=s.note||"";if(s.shot){{img.src=s.shot;img.hidden=false}}
sel.onchange=function(){{(st[id]=st[id]||{{}}).status=sel.value;save()}};txt.oninput=function(){{(st[id]=st[id]||{{}}).note=txt.value;save()}};
file.onchange=function(){{var f=file.files[0];if(!f)return;var r=new FileReader();r.onload=function(){{img.src=r.result;img.hidden=false;
(st[id]=st[id]||{{}}).shot=r.result;save()}};r.readAsDataURL(f)}};}});
document.getElementById("export").onclick=function(){{var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(st,null,1)],{{type:"application/json"}}));
a.download="checklist.json";a.click()}};}})();</script>""", [])
