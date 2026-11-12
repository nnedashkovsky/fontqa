"""issues.json -> report.xlsx, the working table for fixing a release.

Sheets: Summary, Issues, Symptoms, Confirmed OK, Fonts,
Matrix, Coverage, Legend (Changes comes with run-to-run comparison in phase 5).
Status and Comment columns are left for the designer; later runs will carry
them over by the issue key, which is why the key is in the sheet too.

openpyxl is pure Python, so the same code writes the file in the browser.
"""

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .report_html import ACTION_LABEL, LEGEND

ACCENT = "1F6F5C"
FILL = {
    "head": PatternFill("solid", fgColor="E0EFE9"),
    "fix": PatternFill("solid", fgColor="F8E4E1"),
    "confirm": PatternFill("solid", fgColor="FAEEE0"),
    "ok": PatternFill("solid", fgColor="E0EFE9"),
    "out": PatternFill("solid", fgColor="FAEEE0"),
}
CELL_FILL = {"×": FILL["fix"], "△": FILL["confirm"], "○": FILL["ok"]}
BOLD = Font(bold=True)
HEAD_FONT = Font(bold=True, color=ACCENT)
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")


def _sheet(wb, title, header, rows, widths, wrap=(), freeze="A2"):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill, c.alignment = HEAD_FONT, FILL["head"], WRAP
    for row in rows:
        ws.append(["" if v is None else v for v in row])
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in wrap:
        for cell in ws[get_column_letter(col)][1:]:
            cell.alignment = WRAP
    if freeze:
        ws.freeze_panes = freeze
    if rows:
        ws.auto_filter.ref = ws.dimensions
    return ws


def render(r):
    wb = Workbook()
    wb.remove(wb.active)
    s = r["summary"]

    # ---- Summary
    ws = wb.create_sheet("Summary")
    ws.append(["Inspection report", r["title"]])
    ws["A1"].font = Font(bold=True, size=14, color=ACCENT)
    for k, v in [("Date", r["date"]), ("Profile", r["profile"]),
                 ("Tool", f"Font QA core {r['environment']['core']} · {r['environment']['env']} · fontTools {r['environment']['fontTools']}"),
                 ("Files", f"{r['inventory']['files']} ({', '.join(f'{k} {v}' for k, v in r['inventory']['formats'].items())})"),
                 ("Font Bakery", "universal profile" if r["options"].get("fontbakery") else "not performed"),
                 ("OTS", "performed" if r["options"].get("ots") else "not performed"),
                 ("Not performed", ", ".join(s["not_performed"]) or "—"),
                 ("Not applicable", ", ".join(s.get("not_applicable", [])) or "—"),
                 ("Issues", f"{s['issues']}: fix {s['by_action']['fix']}, confirm {s['by_action']['confirm']}, harmless {s['by_action']['ok']}"),
                 ("Predicted symptoms", s["symptoms"])]:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = BOLD
    ws.append([])
    ws.append(["Category", "Fix", "Confirm", "Harmless", "Symptoms", "Checks", "Confirmed normal"])
    hr = ws.max_row
    for c in ws[hr]:
        c.font, c.fill = HEAD_FONT, FILL["head"]
    for cat, name in r["categories"].items():
        b = s["by_category"][cat]
        if b["checks"]:
            ws.append([f"{cat} {name}", b["fix"], b["confirm"], b["ok"], b["symptoms"], b["checks"], "; ".join(b["confirmed"])])
            ws.cell(ws.max_row, 7).alignment = WRAP
    ws.append([])
    ws.append(["Inputs (SHA-256)"])
    ws.cell(ws.max_row, 1).font = BOLD
    for x in r["inputs"]:
        ws.append([x["path"], x["sha256"], x["size"], f"{x['lineage'] or '—'} {x['format']}"])
    for col, w in zip("ABCDEFG", (34, 60, 12, 12, 12, 10, 80)):
        ws.column_dimensions[col].width = w

    # ---- Issues
    rows = []
    for i in r["issues"]:
        by_file = "\n".join(f"{f}: {m}" for f, m in i["measured_by_file"].items())
        rows.append([i["id"], i["category"], i["classification"], i["summary"], ACTION_LABEL[i["action"]],
                     i["severity"].title(), i["judgment"], i["expected"],
                     i["measured"] + (f"\n{by_file}" if by_file else ""), i["basis"], len(i["files"]),
                     i["files_summary"], "\n".join(i["files"]), ", ".join(i["glyphs"][:150]) + (" …" if i["glyph_count"] > 150 else ""),
                     i["fix"], ", ".join(i["symptoms"]), i["status"], i["comment"], i["first_seen"], i["last_seen"], i["key"]])
    ws = _sheet(wb, "Issues", ["No.", "Cat.", "Classification", "Issue (summary)", "Action", "Severity", "Judgment",
                               "Expected", "Measured", "Basis for comparison", "Files", "Files (summary)", "Applicable files",
                               "Glyphs / code points", "Suggested fix direction", "Symptoms", "Status", "Comment",
                               "First seen", "Last seen", "Key"],
                rows, (7, 5, 34, 46, 9, 9, 8, 26, 34, 46, 6, 24, 46, 46, 46, 10, 12, 30, 11, 11, 30),
                wrap=(3, 4, 8, 9, 10, 12, 13, 14, 15), freeze="E2")
    for row in ws.iter_rows(min_row=2):
        action = next(k for k, v in ACTION_LABEL.items() if v == row[4].value)
        row[4].fill = FILL[action]
        for c in row:
            if c.alignment != WRAP:
                c.alignment = TOP

    # ---- Symptoms
    _sheet(wb, "Symptoms", ["No.", "Environment", "Symptom", "Parent issue", "Status", "Screenshot"],
           [[x["id"], x["environment"], x["symptom"], x["parent"], x["status"], x["screenshot"]] for x in r["symptoms"]],
           (7, 30, 70, 12, 12, 30), wrap=(3,))

    # ---- Confirmed OK
    _sheet(wb, "Confirmed OK", ["Cat.", "Check", "What was verified", "Basis", "Passed", "Flagged", "N/A", "Errors"],
           [[c["category"], c["title"], c["what"], c["basis"], c["files_passed"], c["files_flagged"], c["files_na"],
             c["files_error"]] for c in r["checks"]],
           (5, 40, 60, 60, 8, 8, 8, 8), wrap=(2, 3, 4))

    # ---- Fonts
    fields = r["fonts"]["fields"]
    ws = _sheet(wb, "Fonts", ["File", "Lineage", "Format", "Family", "Style"] + fields,
                [[x["path"], x["lineage"], x["format"], x["family"], x["style"]] + [x["values"][k] for k in fields]
                 for x in r["fonts"]["rows"]],
                [50, 9, 8, 22, 18] + [14] * len(fields), freeze="B2")
    for n, x in enumerate(r["fonts"]["rows"], 2):
        for k in x["outliers"]:
            ws.cell(n, 6 + fields.index(k)).fill = FILL["out"]

    # ---- Matrix
    m = r["matrix"]
    ws = _sheet(wb, "Matrix", ["File"] + m["checks"], [[f] + cells for f, cells in zip(m["files"], m["cells"])],
                [50] + [4] * len(m["checks"]), freeze="B2")
    for c in ws[1][1:]:
        c.alignment = Alignment(text_rotation=90, vertical="bottom")
    ws.row_dimensions[1].height = 150
    for row in ws.iter_rows(min_row=2, min_col=2):
        for c in row:
            c.alignment = Alignment(horizontal="center")
            if c.value in CELL_FILL:
                c.fill = CELL_FILL[c.value]

    # ---- Coverage
    if r["coverage"]:
        names = list(r["coverage"][0]["sets"])
        _sheet(wb, "Coverage", ["File", "Family", "Style"] + names + ["Next level", "Missing for next level"],
               [[c["path"], c["family"], c["style"]] + [f"{h}/{t}" for h, t in (c["sets"][n] for n in names)]
                + [c["next_level"] or "complete", " ".join(c["missing_for_next"])] for c in r["coverage"]],
               [44, 20, 18] + [14] * len(names) + [16, 80], wrap=(len(names) + 5,))

    # ---- Legend
    ws = wb.create_sheet("Legend")
    for axis, rows in LEGEND.items():
        ws.append([axis])
        ws.cell(ws.max_row, 1).font = HEAD_FONT
        for k, v in rows:
            ws.append([k, v])
        ws.append([])
    ws.append(["Categories"])
    ws.cell(ws.max_row, 1).font = HEAD_FONT
    for k, v in r["categories"].items():
        ws.append([k, v])
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 110

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
