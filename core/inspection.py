"""Inspection: run a profile's checks over a delivery and turn hits into issues.

The result is issues.json — the single source the HTML report, the xlsx and
any later comparison are built from (so the report languages and the sheets
can never disagree, which happens with separately written reports).

Order of work: fonts are visited one at a time for file and outline checks and
their parsed tables are dropped afterwards; family and package checks then run
on the light caches (cmap, widths). Every (check, file) pair ends with a status
— fix / confirm / harmless / pass / n/a / error — which feeds the matrix and the
"confirmed OK" list: a report says what is fine, not only what is wrong.
"""

import datetime
import json
import inspect as pyinspect  # stdlib; this module is core.inspection
from collections import Counter, defaultdict

from . import VERSION, inventory, rules
from .checks import CATEGORIES, REGISTRY, families, in_level, load_all, preset_prefixes
from .fontview import FontView, assign_outline_keys

ACTION_ORDER = {"fix": 0, "confirm": 1, "ok": 2}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
ACTION_LABEL = {"fix": "Fix", "confirm": "Confirm", "ok": "Harmless"}
CELL = {"fix": "×", "confirm": "△", "ok": "○", "pass": "○", "n/a": "—", "error": "!"}


def run(paths, profile="release", ots=None, fontbakery=None, font_json=None, facts=None,
        progress=None, today=None, only=None, level="engineer", preset=None):
    """Inspect (abs path, relpath) pairs; returns the issues.json dict.

    `only` is a list of check-id prefixes ("vf.", "names.gdi_length") to run a subset.
    `preset` names a selection from checks.PRESETS; it cannot be combined with `only`.
    `level` is "designer" (the drawing checks) or "engineer" (everything); see core/levels.py.
    """
    load_all()
    facts = facts or inventory.facts_for(paths)
    inv = inventory.build(facts)
    by_rel = {f["path"]: f for f in inv["files"]}
    views = [FontView(p, by_rel[r]) for p, r in paths]
    ctx = {"fontbakery": fontbakery, "font_json": font_json, "ots": ots}
    for v in views:
        v.ctx_ots = (ots or {}).get(v.rel)

    if level not in ("designer", "engineer"):
        raise ValueError(f"unknown level {level!r}")
    if level == "designer":
        fontbakery = font_json = None  # file-level inputs; their checks do not run
        ctx = {"fontbakery": None, "font_json": None, "ots": ots}
    if preset and only:
        raise ValueError("preset and only cannot be combined")
    if preset:
        only = preset_prefixes(preset)
    available = [c for c in REGISTRY if profile in c.profiles and in_level(c, level)]
    checks = [c for c in available if not only or any(c.id.startswith(p) for p in only)]
    if only and not checks:
        raise ValueError(f"no check of the {level} level matches {', '.join(only)}")
    status = defaultdict(dict)
    hits, errors = [], []

    def performed(c):
        return all(ctx.get(r) for r in c.requires)

    def record(c, hs, files_default, members):
        worst = None
        hit_files = set()
        for h in hs:
            files = h.files or files_default
            hits.append((c, h, files))
            hit_files.update(files)
            a = h.action or c.action
            worst = a if worst is None or ACTION_ORDER[a] < ACTION_ORDER[worst] else worst
        for rel in members:
            if rel in hit_files:
                acts = [h.action or c.action for h in hs if rel in (h.files or files_default)]
                status[c.id][rel] = min(acts, key=ACTION_ORDER.get)
            else:
                status[c.id].setdefault(rel, "pass")

    def safe(c, fn, *args):
        try:
            return list(fn(*args))
        except Exception as exc:  # a broken check must not hide the others
            errors.append({"check": c.id, "error": f"{type(exc).__name__}: {exc}"[:300]})
            return None

    # ---- file and outline checks, one font at a time
    file_checks = [c for c in checks if c.scope == "file"]
    outline_checks = [c for c in checks if c.scope == "outline"]
    sharing = defaultdict(list)
    assign_outline_keys(views)
    # a variable font never shares its group with a static one, even when the default master's
    # outlines are byte-identical to a static font: the variable checks must still see it
    share_key = lambda x: (x.outline_key, bool(x.variable))
    for v in views:
        if v.ok:
            sharing[share_key(v)].append(v)
            v.release()
    # the first member of each group must be an sfnt/WOFF whenever there is one
    for key, group in sharing.items():
        group.sort(key=lambda x: x.fmt == "WOFF2")
    views_order = sorted(views, key=lambda x: not (x.ok and sharing[share_key(x)][0] is x))
    for n, v in enumerate(views_order):
        if progress:
            progress(n, len(views), v.rel)
        for c in file_checks:
            if not (performed(c) and c.applicable(v)):
                status[c.id][v.rel] = "n/a"
                continue
            hs = safe(c, c.fn, v)
            if hs is None:
                status[c.id][v.rel] = "error"
            else:
                record(c, hs, [v.rel], [v.rel])
        group = sharing.get(share_key(v)) if v.ok else None
        if group and group[0] is v:
            members = [x.rel for x in group]
            for c in outline_checks:
                if not (performed(c) and c.applicable(v)):
                    for rel in members:
                        status[c.id][rel] = "n/a"
                    continue
                hs = safe(c, c.fn, v)
                if hs is None:
                    for rel in members:
                        status[c.id][rel] = "error"
                else:
                    record(c, hs, members, members)
        elif not v.ok:
            for c in outline_checks:
                status[c.id][v.rel] = "n/a"
        v.release()

    # ---- family and package checks on the light caches
    for c in checks:
        if c.scope == "family":
            for group in families(views):
                members = [v for v in group if c.applicable(v)]
                if not members or not performed(c):
                    continue
                hs = safe(c, c.fn, members)
                if hs is not None:
                    record(c, hs, [v.rel for v in members], [v.rel for v in members])
        elif c.scope == "package":
            members = [v.rel for v in views if v.ok]
            if not performed(c):
                for rel in members:
                    status[c.id][rel] = "n/a"
                continue
            fn_args = (views, ctx) if "ctx" in pyinspect.signature(c.fn).parameters else (views,)
            hs = safe(c, c.fn, *fn_args)
            if hs is not None:
                record(c, hs, members, members)
        for v in views:
            if v.ok:
                status[c.id].setdefault(v.rel, "n/a")

    issues, symptoms = _aggregate(hits, today)
    if level == "engineer":
        menus, symptoms = _menus(views, issues, symptoms, {c.id for c in checks})
    else:  # the menu simulation reads names and tables: an engineer's view
        menus = None
    result = {
        "schema": "fontqa/issues 1",
        "title": _title(views),
        "date": today or datetime.date.today().isoformat(),
        "profile": profile,
        "level": level,
        # a partial run says so in every report: its counts are not comparable with a full one
        "scope": {"preset": preset, "selection": list(only) if only and not preset else None,
                  "run": len(checks), "available": len(available), "partial": len(checks) < len(available)},
        "environment": inventory.environment(),
        "options": {"fontbakery": bool(fontbakery), "ots": "provided" if ots else None,
                    "font_json": bool(font_json)},
        "inputs": [{"path": f["path"], "format": f.get("format"), "lineage": f.get("lineage"),
                    "size": f["size"], "sha256": f["sha256"], "error": f.get("error")} for f in inv["files"]],
        "inventory": inv["summary"],
        "categories": CATEGORIES,
        "checks": [_check_meta(c, status, performed(c)) for c in checks],
        "issues": issues,
        "symptoms": symptoms,
        "menus": menus,
        "matrix": _matrix(checks, views, status),
        "fonts": _fonts_table(views),
        "charsets": _charsets(views),
        "languages": _languages(views),
        "errors": errors,
    }
    result["summary"] = _summary(result)
    return result


# ------------------------------------------------------------------ aggregation

def _aggregate(hits, today):
    groups = {}
    for c, h, files in hits:
        g = groups.setdefault((c.id, h.key), {"check": c, "hits": []})
        g["hits"].append((h, files))
    rows = []
    for (cid, key), g in groups.items():
        c, hs = g["check"], g["hits"]
        files = sorted({f for _, fs in hs for f in fs})
        action = min((h.action or c.action for h, _ in hs), key=ACTION_ORDER.get)
        severity = min((h.severity or c.severity for h, _ in hs), key=SEVERITY_ORDER.get)
        judgment = next((h.judgment for h, _ in hs if h.judgment), None) or ("△" if action == "confirm" and c.judgment == "×" else c.judgment)
        measured = {str(h.measured) for h, _ in hs}
        by_file = {}
        if len(measured) > 1:
            for h, fs in hs:
                for f in fs:
                    by_file[f] = str(h.measured)
        glyphs = []
        for h, _ in hs:
            for gl in h.glyphs:
                if gl not in glyphs:
                    glyphs.append(gl)
        summaries = {h.summary[:1].upper() + h.summary[1:] for h, _ in hs}
        rows.append({
            "key": f"{cid}|{key}",
            "check": cid,
            "category": c.category,
            "classification": c.classification,
            "title": c.title,
            "summary": next(iter(summaries)) if len(summaries) == 1 else f"{key[0].upper()}{key[1:]} ({len(files)} files)",
            "action": action,
            "severity": severity,
            "judgment": judgment,
            "expected": str(hs[0][0].expected) if hs[0][0].expected is not None else "",
            "measured": next(iter(measured)) if len(measured) == 1 else "varies by file",
            "measured_by_file": dict(sorted(by_file.items())),
            "basis": c.basis,
            "fix": c.fix,
            "files": files,
            "files_summary": _files_summary(files),
            "glyphs": glyphs[:400],
            "glyph_count": len(glyphs),
            "symptoms": [],
            "status": "",
            "comment": "",
            "first_seen": today or datetime.date.today().isoformat(),
            "last_seen": today or datetime.date.today().isoformat(),
            "_symptom_texts": list(c.symptoms),
            "rule": rules.for_issue(cid),
        })
    rows.sort(key=lambda r: (ACTION_ORDER[r["action"]], SEVERITY_ORDER[r["severity"]], r["category"], r["check"], r["key"]))
    symptoms = []
    for i, r in enumerate(rows, 1):
        r["id"] = f"P-{i:02d}"
        for text in r.pop("_symptom_texts"):
            sid = f"S-{len(symptoms) + 1:02d}"
            env, _, what = text.partition(": ") if ": " in text else ("", "", text)
            symptoms.append({"id": sid, "parent": r["id"], "environment": env, "symptom": what or text,
                             "status": "predicted", "screenshot": ""})
            r["symptoms"].append(sid)
    return rows, symptoms


def _menus(views, issues, generic, ran):
    """Simulated menus, and symptoms: concrete ones from the simulation, generic ones for the rest."""
    from . import menus as mn
    try:
        sim = mn.simulate(views)
    except Exception as exc:  # a simulation problem must not cost the report
        return {"error": f"{type(exc).__name__}: {exc}"}, generic
    # a symptom belongs to a check: when that check did not run (a partial run), its symptom is not reported
    concrete = [s for s in mn.symptoms(sim, issues) if s["check"] in ran]
    covered = {s["check"] for s in concrete}
    by_id = {i["id"]: i for i in issues}
    keep = [s for s in generic if by_id[s["parent"]]["check"] not in covered]
    out = concrete + keep
    for i in issues:
        i["symptoms"] = []
    for k, s in enumerate(out, 1):
        s["id"] = f"S-{k:02d}"
        if s["parent"] in by_id:
            by_id[s["parent"]]["symptoms"].append(s["id"])
    return sim, out


def _files_summary(files):
    """'Desktop TTF 12 · Web WOFF2 12' from relative paths."""
    from .inventory import lineage
    counts = Counter()
    for f in files:
        ext = f.rsplit(".", 1)[-1].upper()
        counts[(lineage(f, ext if ext in ("WOFF", "WOFF2") else None) or "—", ext)] += 1
    return " · ".join(f"{lin + ' ' if lin != '—' else ''}{ext} {n}" for (lin, ext), n in sorted(counts.items()))


def _title(views):
    """'Acme Sans' for Acme Sans, Acme Sans App, Acme Sans VF…: the shared words."""
    fams = []
    for v in views:
        fam = v.names.get("16") or v.family
        if v.ok and fam and fam not in fams and len(fam) > 1 and fam.isprintable():
            fams.append(fam)
    if len(fams) <= 1:
        return fams[0] if fams else ""
    words = [f.split() for f in fams]
    common = []
    for parts in zip(*words):
        if len(set(parts)) != 1:
            break
        common.append(parts[0])
    return " ".join(common) if common else f"{fams[0]} and {len(fams) - 1} more"


def _check_meta(c, status, performed=True):
    st = Counter(status[c.id].values())
    return {"id": c.id, "category": c.category, "title": c.title, "classification": c.classification,
            "performed": performed, "requires": list(c.requires),
            "scope": c.scope, "what": c.what, "basis": c.basis, "default_action": c.action,
            "default_severity": c.severity,
            "files_checked": sum(n for k, n in st.items() if k != "n/a"),
            "files_passed": st.get("pass", 0) + st.get("ok", 0),
            "files_flagged": st.get("fix", 0) + st.get("confirm", 0),
            "files_na": st.get("n/a", 0), "files_error": st.get("error", 0)}


def _matrix(checks, views, status):
    files = [v.rel for v in views]
    return {"checks": [c.id for c in checks], "files": files,
            "cells": [[CELL[status[c.id].get(f, "n/a")] for c in checks] for f in files]}


FONT_FIELDS = [
    ("ID 1", lambda f: f["names"]["windows"].get("1")), ("ID 2", lambda f: f["names"]["windows"].get("2")),
    ("ID 16", lambda f: f["names"]["windows"].get("16")), ("ID 17", lambda f: f["names"]["windows"].get("17")),
    ("ID 4", lambda f: f["names"]["windows"].get("4")), ("ID 6", lambda f: f["names"]["windows"].get("6")),
    ("Version", lambda f: (f["names"]["windows"].get("5") or "").split(";")[0]),
    ("Weight", lambda f: f["style"]["weight_class"]), ("Width", lambda f: f["style"]["width_class"]),
    ("fsSelection", lambda f: " ".join(f["style"]["fs_selection"] or [])), ("fsType", lambda f: f["style"]["fs_type"]),
    ("Vendor", lambda f: f["style"]["vendor"]), ("UPM", lambda f: f["metrics"]["upm"]),
    ("hhea", lambda f: " / ".join(map(str, f["metrics"]["hhea"]))),
    ("typo", lambda f: " / ".join(map(str, f["metrics"].get("typo") or []))),
    ("win", lambda f: " / ".join(map(str, f["metrics"].get("win") or []))),
    ("x-height", lambda f: f["metrics"].get("x_height")), ("Cap height", lambda f: f["metrics"].get("cap_height")),
    ("Glyphs", lambda f: f["glyphs"]["count"]), ("Characters", lambda f: f["glyphs"]["cmap"]),
    ("GSUB features", lambda f: " ".join(((f.get("layout") or {}).get("GSUB") or {}).get("features", []))),
    ("GPOS features", lambda f: " ".join(((f.get("layout") or {}).get("GPOS") or {}).get("features", []))),
]
# fields that should agree within a family; a tuple, so outliers are listed in a stable order
FAMILY_WIDE = tuple(k for k, _ in FONT_FIELDS if k in {"ID 16", "Version", "Vendor", "UPM", "hhea", "typo", "win",
                                                       "x-height", "Cap height", "Glyphs", "Characters"})


def _fonts_table(views):
    rows = {}
    for v in views:
        if not v.ok:
            continue
        rows[v.rel] = {"path": v.rel, "format": v.fmt, "lineage": v.lineage or "—", "family": v.family,
                       "style": v.subfamily, "values": {k: get(v.facts) for k, get in FONT_FIELDS}, "outliers": []}
    for group in families(views):
        if len(group) < 2:
            continue
        for k in FAMILY_WIDE:
            vals = Counter(str(rows[v.rel]["values"][k]) for v in group)
            if len(vals) > 1:
                top = vals.most_common(1)[0][0]
                for v in group:
                    if str(rows[v.rel]["values"][k]) != top:
                        rows[v.rel]["outliers"].append(k)
    return {"fields": [k for k, _ in FONT_FIELDS], "rows": list(rows.values())}


def _charsets(views):
    """How much of every named character set each style has; styles with the same answer share a group.

    Missing code points are stored as ranges: whole blocks missing stay a few numbers.
    """
    from . import charsets as cs
    db = cs.database()
    groups = {}
    for v in views:
        if not (v.ok and v.is_sfnt):
            continue
        cov = cs.coverage(v.cmap)
        have = {n: c["have"] for n, c in cov.items()}
        missing = {n: cs.ranges(c["missing"]) for n, c in cov.items() if c["missing"]}
        key = json.dumps([have, missing])
        label = f"{v.family} {v.subfamily}" + (" (variable)" if v.variable else "")
        groups.setdefault(key, {"styles": set(), "have": have, "missing": missing})["styles"].add(label)
        v.release()
    out = sorted(({"styles": sorted(g["styles"]), "have": g["have"], "missing": g["missing"]} for g in groups.values()),
                 key=lambda g: g["styles"])
    return {"source": db["source"],
            "sets": {n: {"script": db["meta"][n]["script"], "group": db["meta"][n]["group"], "note": db["meta"][n]["note"],
                         "total": len(c)} for n, c in db["sets"].items()},
            "groups": out}


def _languages(views):
    """Languages each style supports, and those it is partly short of (from 40%); styles with the same answer share a group."""
    from . import languages as lg
    from .checks.charset import language_view
    groups, used = {}, {}
    for v in views:
        if not (v.ok and v.is_sfnt):
            continue
        cov = language_view(v)
        supported = sorted(x["tag"] for x in cov["supported"])
        partial = sorted(({"tag": a["lang"]["tag"], "missing": a["missing"], "need": a["need"],
                           "have": a["total"] - a["letters"], "total": a["total"]} for a in cov["partial"]), key=lambda a: a["tag"])
        key = json.dumps([supported, partial], ensure_ascii=False)
        label = f"{v.family} {v.subfamily}" + (" (variable)" if v.variable else "")
        groups.setdefault(key, {"styles": set(), "supported": supported, "partial": partial})["styles"].add(label)
        for x in cov["supported"] + [a["lang"] for a in cov["partial"]]:
            used[x["tag"]] = x
        v.release()
    db = lg.database()
    out = sorted(({"styles": sorted(g["styles"]), "supported": g["supported"], "partial": g["partial"]} for g in groups.values()),
                 key=lambda g: g["styles"])
    return {"source": db["source"], "min_speakers_for_findings": lg.ALMOST_MIN_SPEAKERS, "groups": out,
            "names": {t: {"name": x["name"], "script": x["script"], "speakers": x["speakers"], "regions": x["regions"],
                          "letters": len(x["letters"])}
                      for t, x in sorted(used.items())},
            "scripts": db["scripts"]}


def _summary(result):
    table = {}
    for cat in CATEGORIES:
        row = {"fix": 0, "confirm": 0, "ok": 0, "symptoms": 0}
        for i in result["issues"]:
            if i["category"] == cat:
                row[i["action"]] += 1
                row["symptoms"] += len(i["symptoms"])
        row["checks"] = sum(1 for c in result["checks"] if c["category"] == cat)
        # passed: ran on some file and found nothing; flagged: gave findings (with their numbers)
        # (a harmless finding is a finding: that check is flagged, not passed)
        with_issues = {i["check"] for i in result["issues"]}
        row["passed"] = [c["title"] for c in result["checks"] if c["category"] == cat and c["id"] not in with_issues
                         and c["files_checked"] and not c["files_flagged"] and not c["files_error"]]
        row["confirmed"] = row["passed"]  # the name before 0.4; drop one version later
        row["flagged"] = []
        for c in result["checks"]:
            if c["category"] != cat:
                continue
            found = [i for i in result["issues"] if i["check"] == c["id"]]
            if found:
                worst = min((i["action"] for i in found), key=ACTION_ORDER.get)
                row["flagged"].append({"check": c["id"], "title": c["title"], "issues": [i["id"] for i in found],
                                       "action": worst})
        table[cat] = row
    counts = Counter((i["action"], i["severity"]) for i in result["issues"])
    return {"by_category": table, "issues": len(result["issues"]), "symptoms": len(result["symptoms"]),
            "by_action": {a: sum(n for (x, _), n in counts.items() if x == a) for a in ACTION_ORDER},
            "by_severity": {s: sum(n for (_, y), n in counts.items() if y == s) for s in SEVERITY_ORDER},
            "not_performed": [c["title"] for c in result["checks"] if not c["performed"]],
            "not_applicable": [c["title"] for c in result["checks"] if c["performed"] and c["files_checked"] == 0]}
