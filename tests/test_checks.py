"""Every check fires on a font broken for it, and stays silent on the clean set.

CASES maps a check id to a function that builds broken fonts in a folder and
may return inputs for the run (ots, fontbakery, font_json) or `expect`, a text
the finding's summary must contain. A new check needs a case here: the
coverage test fails otherwise.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import fontkit as fk  # noqa: E402
from core import inventory  # noqa: E402
from core.checks import load_all  # noqa: E402
from core.inspection import run  # noqa: E402

W = fk.western()
ASCII = list(range(0x20, 0x7F))
CYRILLIC = list(range(0x410, 0x450))
DIGITS_TF = {f"uni{c:04X}.tf": (fk.WIDTH, fk.CAP) for c in range(0x30, 0x3A)}
TNUM = "feature tnum {\n" + "".join(f"  sub uni{c:04X} by uni{c:04X}.tf;\n" for c in range(0x30, 0x3A)) + "} tnum;\n"
LANGS = "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n"
KERN = "feature kern { pos uni0041 uni0056 -50; } kern;\n"
FEA_CLEAN = (LANGS + "markClass uni0301 <anchor 300 700> @top;\n"
             "feature aalt { feature tnum; } aalt;\n" + TNUM + KERN +
             "feature mark { pos base uni0041 <anchor 300 700> mark @top; } mark;\n"
             "table GDEF { GlyphClassDef [uni0041], , [uni0301], ; } GDEF;\n")


def add_legacy_kern(font):
    from fontTools.ttLib import newTable
    from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0
    table = newTable("kern")
    table.version = 0
    sub = KernTable_format_0()
    sub.version, sub.coverage, sub.format, sub.tupleIndex = 0, 1, 0, None
    sub.kernTable = {("uni0041", "uni0056"): -50}
    table.kernTables = [sub]
    font["kern"] = table


def one(folder, name="TestSans-Regular.ttf", line="Desktop", **kw):
    return fk.build(os.path.join(folder, line, name), **kw)


def features_font(folder, **kw):
    """One font with tnum, aalt, kern (GPOS and legacy), mark and a combining mark."""
    args = dict(family="Test Feat", chars=W + [0x301], widths={0x301: 0}, extra_glyphs=DIGITS_TF,
                fea=FEA_CLEAN, mutate=add_legacy_kern)
    args.update(kw)
    return one(folder, "TestFeat-Regular.ttf", **args)


def inspect(folder, only=None, level="engineer", **ctx):
    paths = inventory.collect([str(folder)])
    verdict = ctx.pop("ots", "ok")  # one OTS verdict for every file
    ctx["ots"] = {rel: verdict for _, rel in paths}
    return run(paths, only=only, level=level, **ctx)


# ------------------------------------------------------------------ broken fonts

def _quad_bulge(pen):
    pen.moveTo((50, 0))
    pen.qCurveTo((300, 900), (550, 0))
    pen.closePath()


def _doubled_point(pen):
    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((50, 700))
    pen.lineTo((550, 700))
    pen.lineTo((550, 0))
    pen.closePath()


def _fractional(pen):
    pen.moveTo((50.5, 0))
    pen.lineTo((50.5, 700))
    pen.lineTo((550, 700))
    pen.lineTo((550, 0))
    pen.closePath()


def _rotated_start(pen):
    """The Bold master's box, starting from another corner."""
    pen.moveTo((570, 700))
    pen.lineTo((570, 0))
    pen.lineTo((30, 0))
    pen.lineTo((30, 700))
    pen.closePath()


def _default_instance(font):
    font["fvar"].instances[0].subfamilyNameID = font["name"].addName("Light")


def _same_instance_names(font):
    inst = font["fvar"].instances
    inst[1].subfamilyNameID = inst[0].subfamilyNameID


def _mac_name(font):
    font["name"].setName("Another Name", 1, 1, 0, 0)


def _localized(font):
    fk.set_name(font, 1, "测试", 0x804)
    fk.set_name(font, 2, "Regular", 0x804)


def _set(table, **fields):
    def mutate(font):
        for k, v in fields.items():
            setattr(font[table], k, v)
    return mutate


def _drop(table):
    def mutate(font):
        del font[table]
    return mutate


CASES = {
    # names
    "names.gdi_length": lambda d: one(d, family="Test Sans With A Very Long Family Name"),
    "names.ribbi": lambda d: one(d, names={"styleName": "Light"}),
    "names.wws": lambda d: fk.family(d, styles=("Display Bold",)),
    "names.localized": lambda d: fk.family(d, styles=("Light",), mutate=_localized),
    "names.unique": lambda d: [one(d, "A.ttf"), one(d, "B.ttf")],
    "names.required": lambda d: one(d, mutate=lambda f: fk.drop_name(f, 5)),
    "names.postscript": lambda d: one(d, names={"psName": "Test Sans-Regular"}),
    "names.full_name": lambda d: one(d, names={"fullName": "Test Sans " + "Very " * 12 + "Long"}),
    "names.version": lambda d: one(d, names={"version": "1.000"}),
    "names.mac_mirror": lambda d: one(d, mutate=_mac_name),
    "names.family_consistent": lambda d: fk.family(d, per_style={"Bold": {"names": {"copyright": "Someone else"}}}),
    "tables.meta": lambda d: one(d, chars=ASCII + list(range(0x400, 0x500))),
    # character set and glyphs
    "charset.family_same": lambda d: fk.family(d, per_style={"Bold": {"chars": [c for c in W if c != 0x20AC]}}),
    "charset.store_minimum": lambda d: one(d, chars=[c for c in W if c != 0x20AC]),
    # a Windows-1252 font lacks ő ű: Hungarian is one step away
    "charset.languages_almost": lambda d: one(d),
    "glyphs.empty_mapped": lambda d: one(d, empty={0x41}),
    "glyphs.notdef": lambda d: one(d, shapes={".notdef": lambda pen: None}),
    "glyphs.spaces": lambda d: one(d, widths={0xA0: 400}),
    "glyphs.tabular": lambda d: features_font(d, widths={0x301: 0, "uni0031.tf": 580}),
    "glyphs.mark_widths": lambda d: features_font(d, widths={0x301: 200}),
    "widths.near_equal": lambda d: fk.family(d, styles=("Light", "Regular", "Bold"),
                                             per_style={"Light": {"widths": {0x41: 601}}}),
    # outlines
    "outline.extrema": lambda d: one(d, shapes={0x4F: _quad_bulge}),
    "outline.zero_length": lambda d: one(d, shapes={0x41: _doubled_point}),
    "outline.fractional": lambda d: one(d, "TestSans-Regular.otf", cff=True, shapes={0x41: _fractional}),
    # layout
    "layout.kern_shadowed": lambda d: one(d, fea=LANGS + (
        "feature kern {\n  pos [uni0041 uni0056] [uni0041 uni0056] -50;\n  subtable;\n"
        "  pos [uni0041 uni0054] [uni0054 uni0059] -30;\n} kern;\n"), mutate=add_legacy_kern),
    "layout.unreachable": lambda d: one(d, extra_glyphs={"uni0041.ss01": (fk.WIDTH, fk.CAP)}),
    "layout.aalt": lambda d: features_font(d, extra_glyphs=dict(DIGITS_TF, **{"uni0041.ss01": (fk.WIDTH, fk.CAP)}),
                                           fea=FEA_CLEAN + "feature ss01 { sub uni0041 by uni0041.ss01; } ss01;\n"),
    "layout.marks": lambda d: one(d, chars=W + [0x301], widths={0x301: 0}),
    "layout.scripts": lambda d: one(d, chars=W + CYRILLIC, fea=LANGS + KERN, mutate=add_legacy_kern),
    "layout.legacy_kern": lambda d: one(d, fea=LANGS + KERN),
    # table values
    "os2.weight_class": lambda d: one(d, "TestSans-Bold.ttf", style="Bold", os2={"usWeightClass": 400}),
    "os2.width_class": lambda d: one(d, os2={"usWidthClass": 3}),
    "os2.unicode_ranges": lambda d: one(d, mutate=_set("OS/2", ulUnicodeRange1=0)),
    "os2.codepage_ranges": lambda d: one(d, mutate=_set("OS/2", ulCodePageRange1=0)),
    "post.italic": lambda d: one(d, mutate=_set("post", italicAngle=-12)),
    "post.format": lambda d: one(d, "TestSans-Regular.woff2", line="Web", flavor="woff2"),
    "metrics.line_spacing": lambda d: one(d, mutate=_set("hhea", ascent=1200)),
    "metrics.use_typo": lambda d: one(d, os2={"fsSelection": 0x40}),
    "metrics.win_clipping": lambda d: one(d, os2={"usWinAscent": 500}),
    "metrics.x_cap_height": lambda d: one(d, os2={"sxHeight": 400}),
    "metrics.family_vertical": lambda d: fk.family(d, per_style={"Bold": {"os2": {"sTypoAscender": 850}}}),
    "tables.hinting": lambda d: one(d, hinted=False),
    # validators
    "external.ots": lambda d: (one(d), {"ots": "GPOS: failed to parse"})[1],
    "external.fontbakery": lambda d: (one(d), {"fontbakery": {"results": [
        {"check": "com.google.fonts/check/example", "status": "FAIL", "target": "(family)", "message": "broken"}]}})[1],
    # lineages and variable fonts
    "lineage.copies_agree": lambda d: [one(d), one(d, "TestSans-Regular.woff2", line="Web", flavor="woff2",
                                                   post_names=False, widths={0x41: 610})],
    "vf.default_instance": lambda d: fk.variable(d, mutate=_default_instance),
    "vf.instance_names": lambda d: fk.variable(d, mutate=_same_instance_names),
    "vf.stat": lambda d: fk.variable(d, mutate=_drop("STAT")),
    "vf.var_tables": lambda d: (fk.variable(d, mutate=_drop("HVAR")), {"expect": "No HVAR"})[1],
    "vf.interpolation": lambda d: fk.variable(d, statics=False, bold_shapes={0x41: _rotated_start}),
    "vf.vs_static": lambda d: fk.variable(d, static_bold={"widths": {0x41: 620}}),
    # release
    "release.formats": lambda d: fk.family(d, web=False),
    "release.file_names": lambda d: one(d, "Wrong Name.ttf"),
    "release.passport": lambda d: one(d, names={"copyright": None}),
    "release.version": lambda d: one(d, version=0.5),
    "release.font_json": lambda d: (one(d), {"font_json": {"facts": {"styles": [
        {"postscript": "TestSans-Regular", "glyphs": 1, "unicodes": 1}]}}})[1],
}


# ------------------------------------------------------------------ tests

def test_every_check_has_a_case():
    ids = {c.id for c in load_all()}
    assert ids == set(CASES), f"no case: {sorted(ids - set(CASES))}; no such check: {sorted(set(CASES) - ids)}"


@pytest.mark.parametrize("check_id", sorted(CASES))
def test_check_fires(check_id, tmp_path):
    ctx = CASES[check_id](tmp_path)
    ctx = dict(ctx) if isinstance(ctx, dict) else {}
    expect = ctx.pop("expect", None)
    result = inspect(tmp_path, only=[check_id], **ctx)
    assert not result["errors"], result["errors"]
    found = [i for i in result["issues"] if i["check"] == check_id]
    assert found, f"{check_id} did not fire"
    if expect:
        assert any(expect in i["summary"] for i in found), [i["summary"] for i in found]


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    folder = tmp_path_factory.mktemp("clean")
    fk.family(folder)                                   # TrueType, Desktop + Web
    fk.family(folder, name="Test Serif", ext=".otf")    # CFF
    features_font(folder)                               # features, marks, kerning
    fk.build(os.path.join(folder, "Web", "TestFeat-Regular.woff2"), family="Test Feat", chars=W + [0x301],
             widths={0x301: 0}, extra_glyphs=DIGITS_TF, fea=FEA_CLEAN, mutate=add_legacy_kern,
             flavor="woff2", post_names=False)
    fk.variable(folder)                                 # variable font with its statics
    return folder


# Harmless by definition and unavoidable in a font built by fontTools: HVAR has no side-bearing maps.
# The language hint is true of any Latin font that is not complete (here: Windows-1252 lacks ő ű).
ALLOWED_ON_CLEAN = {("vf.var_tables", "HVAR without side-bearing maps"),
                    ("charset.languages_almost", "languages one step away")}
NEED_INPUT = {"external.fontbakery", "release.font_json", "charset.languages_almost"}


def test_clean_set_is_silent(clean):
    result = inspect(clean)
    assert not result["errors"], result["errors"]
    issues = {(i["check"], i["key"].split("|", 1)[1]) for i in result["issues"]}
    assert issues <= ALLOWED_ON_CLEAN, sorted(issues - ALLOWED_ON_CLEAN)


def test_clean_set_exercises_every_check(clean):
    """A check that never applies to the clean set proves nothing by staying silent."""
    result = inspect(clean)
    idle = {c["id"] for c in result["checks"] if not c["files_passed"]} - NEED_INPUT - {"vf.var_tables"}
    assert not idle, f"never passed on the clean set: {sorted(idle)}"


def test_designer_level_runs_the_drawing_checks(clean):
    from core.checks import DESIGNER
    result = inspect(clean, level="designer")
    assert {c["id"] for c in result["checks"]} == set(DESIGNER)
    assert result["menus"] is None


def test_rule_cards_agree_with_the_code():
    from core import rules
    errors, _ = rules.validate(rules.load(), load_all())
    assert not errors, errors


def test_changelog_names_the_current_version():
    from core import VERSION
    with open(os.path.join(HERE, "..", "CHANGELOG.md"), encoding="utf-8") as fh:
        first = next(line for line in fh if line.startswith("## "))
    assert first.startswith(f"## {VERSION} "), f"CHANGELOG starts with {first.strip()!r}, the core is {VERSION}"


def test_summary_separates_flagged_from_passed(tmp_path):
    """Every check of a category is exactly one of: flagged, passed, not performed or not applicable."""
    fk.family(tmp_path)
    fk.build(os.path.join(tmp_path, "Desktop", "Broken-Regular.ttf"), family="Broken Sans With A Very Long Family Name",
             widths={0xA0: 400}, os2={"fsSelection": 0x40})
    result = inspect(tmp_path)
    summary = result["summary"]
    titles = {c["id"]: c["title"] for c in result["checks"]}
    skipped = set(summary["not_performed"]) | set(summary["not_applicable"])
    for cat, row in summary["by_category"].items():
        flagged = {x["title"] for x in row["flagged"]}
        passed = set(row["passed"])
        assert not flagged & passed, (cat, flagged & passed)
        in_cat = {t for c, t in titles.items() if next(k for k in result["checks"] if k["id"] == c)["category"] == cat}
        assert flagged | passed | (in_cat & skipped) == in_cat, (cat, in_cat - flagged - passed - skipped)
    flagged_ids = {x["check"] for row in summary["by_category"].values() for x in row["flagged"]}
    assert flagged_ids == {i["check"] for i in result["issues"]}
    for row in summary["by_category"].values():
        for x in row["flagged"]:
            assert all(i in {p["id"] for p in result["issues"]} for i in x["issues"])


def test_presets_select_the_expected_checks(tmp_path):
    from core.checks import PRESETS, DESIGNER
    fk.family(tmp_path)
    for level in ("designer", "engineer"):
        full = inspect(tmp_path, level=level)
        assert full["scope"]["partial"] is False and full["scope"]["run"] == full["scope"]["available"]
        for name, pr in PRESETS.items():
            if name == "all":
                continue
            paths = inventory.collect([str(tmp_path)])
            try:
                result = run(paths, level=level, preset=name, ots={rel: "ok" for _, rel in paths})
            except ValueError:
                # a preset can be empty at the designer level (e.g. names): that is an error, not a silent full run
                assert not [c for c in load_all() if any(c.id.startswith(x) for x in pr["prefixes"]) and
                            (level == "engineer" or c.id in DESIGNER)]
                continue
            ran = {c["id"] for c in result["checks"]}
            want = {c.id for c in load_all() if any(c.id.startswith(x) for x in pr["prefixes"]) and
                    (level == "engineer" or c.id in DESIGNER)}
            assert ran == want, (level, name)
            assert result["scope"]["preset"] == name
            assert result["scope"]["partial"] == (len(want) < result["scope"]["available"])


def test_partial_run_is_marked_everywhere(tmp_path):
    from core.report_html import render
    from core.report_xlsx import render as render_xlsx
    fk.family(tmp_path)
    paths = inventory.collect([str(tmp_path)])
    result = run(paths, preset="differences", ots={rel: "ok" for _, rel in paths})
    assert result["scope"]["run"] == 6 and result["scope"]["partial"]
    assert "Partial run: 6 of 56 checks" in render(result)
    assert render_xlsx(result)[:2] == b"PK"


def test_unknown_preset_and_conflicts_fail_loudly(tmp_path):
    fk.family(tmp_path)
    paths = inventory.collect([str(tmp_path)])
    with pytest.raises(ValueError):
        run(paths, preset="nope")
    with pytest.raises(ValueError):
        run(paths, preset="names", only=["vf."])
    with pytest.raises(ValueError):
        run(paths, only=["no.such.check"])


def test_partial_run_reports_no_symptoms_of_checks_that_did_not_run(tmp_path):
    fk.family(tmp_path)
    fk.build(os.path.join(tmp_path, "Desktop", "Broken-Regular.ttf"), family="Broken Sans With A Very Long Family Name")
    paths = inventory.collect([str(tmp_path)])
    ots = {rel: "ok" for _, rel in paths}
    full = run(paths, ots=ots)
    assert any(s["check"] == "names.gdi_length" for s in full["symptoms"]), "the clean case for this test is gone"
    partial = run(paths, ots=ots, preset="differences")
    assert partial["issues"] == [] and partial["symptoms"] == []
    only_gdi = run(paths, ots=ots, only=["names.gdi_length"])
    assert {s["check"] for s in only_gdi["symptoms"]} == {"names.gdi_length"}
    assert all(s["parent"] != "—" for s in only_gdi["symptoms"])


def test_check_order_does_not_depend_on_import_order():
    ids = [c.id for c in load_all()]
    assert ids == sorted(ids, key=lambda i: (next(c.category for c in load_all() if c.id == i), i))


# ------------------------------------------------------------------ languages (CLDR)

def test_languages_supported_almost_and_out_of_reach():
    from core import languages as lg
    polish = set(map(ord, "aąbcćdeęfghijklłmnńoóprsśtuwyzźż" + "AĄBCĆDEĘFGHIJKLŁMNŃOÓPRSŚTUWYZŹŻ"))
    full = lg.coverage(polish)
    assert "pl" in {x["tag"] for x in full["supported"]}
    short = lg.coverage(polish - {ord("ł"), ord("Ł")})
    assert "pl" not in {x["tag"] for x in short["supported"]}
    near = {a["lang"]["tag"]: a for a in short["almost"]}
    assert near["pl"]["letters"] == 1 and set(near["pl"]["missing"]) == {"ł", "Ł"}
    far = lg.coverage(set(range(0x20, 0x7F)))
    assert "pl" not in {x["tag"] for x in far["supported"]} | {a["lang"]["tag"] for a in far["almost"]}, "eight letters missing"
    assert "en" in {x["tag"] for x in far["supported"]}


def test_a_composed_letter_counts_only_with_a_mark_feature():
    from core import languages as lg
    base = set(range(0x20, 0x7F)) | {0x301}  # ASCII and a combining acute
    without = {a["lang"]["tag"] for a in lg.coverage(base, compose=False)["almost"]}
    with_mark = lg.coverage(base | {0x300, 0x302, 0x303, 0x308, 0x327, 0x30C, 0x30A}, compose=True)
    assert "es" not in {x["tag"] for x in lg.coverage(base, compose=False)["supported"]}
    assert "es" in {x["tag"] for x in with_mark["supported"]} | {a["lang"]["tag"] for a in with_mark["almost"]}


def test_compact_encoding_round_trips():
    from core import languages as lg
    units = ["a", "b", "c", "d", "e", "ß", "{x}", "\u0301", " ", "ab", "가", "각", "갂", "갃", "간", "\\"]
    assert lg.decode_units(lg.encode_units(units)) == units


def test_cldr_unicode_set_parser():
    sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
    from build_languages import parse_unicode_set
    assert parse_unicode_set("[a ą b-d {ae} \\u0301 é]") == ["a", "ą", "b", "c", "d", "ae", "\u0301", "é"]
    assert parse_unicode_set("[ぁァあア ー]") == list("ぁァあア") + ["ー"]


def test_language_data_is_shipped_with_its_licence():
    from core import languages as lg
    db = lg.database()
    assert "CLDR" in db["source"] and len(db["languages"]) > 200
    with open(os.path.join(HERE, "..", "core", "data", "LICENSE-CLDR.txt"), encoding="utf-8") as fh:
        assert "UNICODE LICENSE" in fh.read().upper()


def test_languages_section_is_in_the_report_and_the_workbook(tmp_path):
    from core.report_html import render
    from core.report_xlsx import render as render_xlsx
    import io, openpyxl
    fk.family(tmp_path)
    result = inspect(tmp_path)
    langs = result["languages"]
    assert langs["groups"] and all(t in langs["names"] for g in langs["groups"] for t in g["supported"])
    assert len(langs["groups"]) == 1, "Regular and Bold (and their web copies) cover the same languages"
    page = render(result)
    assert "<h2>Coverage</h2>" in page and "data-pane='langs'" in page and "id='languages'" in page
    wb = openpyxl.load_workbook(io.BytesIO(render_xlsx(result)))
    assert "Languages" in wb.sheetnames
    statuses = {row[4] for row in wb["Languages"].iter_rows(min_row=2, values_only=True)}
    assert {"supported", "one step away"} <= statuses


def test_partial_coverage_lists_what_to_add():
    from core import languages as lg
    cmap = set(fk.western())
    result = lg.coverage(cmap)
    hungarian = next(a for a in result["partial"] if a["lang"]["tag"] == "hu")
    assert hungarian["need"] == [0x150, 0x151, 0x170, 0x171] and hungarian["total"] - hungarian["letters"] > 20
    assert all((a["total"] - a["letters"]) / a["total"] >= lg.PARTIAL_MIN_SHARE for a in result["partial"])
    assert {a["lang"]["tag"] for a in result["almost"]} <= {a["lang"]["tag"] for a in result["partial"]}
    # a language the font has nothing of is not listed at all
    assert "ko" not in {a["lang"]["tag"] for a in result["partial"]}


def test_language_data_has_regions_and_letter_counts(tmp_path):
    from core import languages as lg
    assert {"EU", "AS", "AM", "AF", "OC"} >= {r for x in lg.database()["languages"] for r in x["regions"]}
    assert all(x["regions"] for x in lg.database()["languages"])
    fk.family(tmp_path)
    langs = inspect(tmp_path)["languages"]
    assert "EU" in langs["names"]["en"]["regions"] and langs["names"]["en"]["letters"] >= 26


def test_report_languages_are_rows_with_filters_and_copyable_letters(tmp_path):
    import re
    from core.report_html import render
    fk.family(tmp_path)
    html = render(inspect(tmp_path))
    row = re.search(r"<div class='lrow [a-z]+' data-name=\"hungarian\".*?</div></div>", html, re.S)
    assert row, "Hungarian is 4 letters short of a Windows-1252 font and gets a row"
    text = row.group(0)
    assert 'data-chars="ŐőŰű"' in text and 'data-names="Ohungarumlaut ohungarumlaut Uhungarumlaut uhungarumlaut"' in text
    assert "Ohungarumlaut" in text and "LATIN CAPITAL LETTER O WITH DOUBLE ACUTE" in text
    assert "data-f='region:EU'" in html and "data-f='status:near'" in html and "data-union='names'" in html
    # a supported language shows its real letter count, not 1/1
    english = re.search(r"data-name=\"english\".*?<div class='lp'>(.*?)</div>", html, re.S).group(1)
    assert "100.0 %" in english and "(26/26)" in english


def test_workbook_languages_sheet_has_percent_and_code_points(tmp_path):
    import io, openpyxl
    from core.report_xlsx import render as render_xlsx
    fk.family(tmp_path)
    wb = openpyxl.load_workbook(io.BytesIO(render_xlsx(inspect(tmp_path))))
    rows = list(wb["Languages"].iter_rows(min_row=1, values_only=True))
    assert rows[0][5] == "Letters covered, %" and rows[0][6] == "Code points to add"
    hu = next(r for r in rows[1:] if r[1] == "Hungarian")
    assert hu[4] in ("one step away", "partial") and "U+0151" in hu[6] and 80 < hu[5] < 100


# ------------------------------------------------------------------ character sets

def test_charset_encoding_round_trips():
    from core import charsets as cs
    cps = {0x20, 0x21, 0x22, 0x41, 0x20AC, 0x1F600, 0x1F601}
    assert cs.decode(cs.encode(cps)) == cps
    assert cs.expand(cs.ranges(sorted(cps))) == sorted(cps)
    assert cs.ranges([1, 2, 3, 9]) == [[1, 3], [9, 9]]


def test_charsets_cover_the_known_sets_and_keep_the_store_minimum():
    from core import charsets as cs
    db = cs.database()
    assert len(db["sets"]) >= 25 and set(db["sets"]) == set(db["meta"])
    assert len(db["sets"]["Western European (cp1252)"]) == 218 and len(db["sets"]["ASCII"]) == 95
    assert db["sets"]["Latin 1 (ISO 8859-1)"] <= db["sets"]["Western European (cp1252)"]
    assert {m["script"] for m in db["meta"].values()} >= {"Latn", "Cyrl", "Grek", "Arab", "Hebr"}
    with open(os.path.join(HERE, "..", "core", "data", "LICENSE-GLYPHSETS.txt"), encoding="utf-8") as fh:
        assert "Apache License" in fh.read()


def test_charset_coverage_counts_and_lists_what_is_missing():
    from core import charsets as cs
    cov = cs.coverage(set(fk.western()))
    assert cov["Western European (cp1252)"] == {"have": 218, "total": 218, "missing": []}
    assert cov["ASCII"]["missing"] == [] and cov["Latin 1 (ISO 8859-1)"]["missing"] == []
    hu = cov["Central European (cp1250)"]
    assert hu["have"] < hu["total"] and 0x151 in hu["missing"] and 0x20AC not in hu["missing"]
    cyr = cov["Cyrillic (cp1251)"]
    assert cyr["have"] < 0.6 * cyr["total"]  # ASCII and shared punctuation only, no Cyrillic letters
    # a project's own set joins the list
    mine = cs.coverage({1, 2}, extra={"Mine": {1, 2, 3}})["Mine"]
    assert mine == {"have": 2, "total": 3, "missing": [3]}


def test_result_charsets_groups_and_stores_missing_as_ranges(tmp_path):
    from core import charsets as cs
    fk.family(tmp_path)
    cset = inspect(tmp_path)["charsets"]
    assert len(cset["groups"]) == 1, "Regular, Bold and their web copies cover the same sets"
    g = cset["groups"][0]
    assert set(g["have"]) == set(cset["sets"])
    assert g["have"]["Western European (cp1252)"] == 218 and "Western European (cp1252)" not in g["missing"]
    assert g["missing"]["Central European (cp1250)"] and all(len(r) == 2 for r in g["missing"]["Central European (cp1250)"])
    total = cset["sets"]["Central European (cp1250)"]["total"]
    assert g["have"]["Central European (cp1250)"] + len(cs.expand(g["missing"]["Central European (cp1250)"])) == total


def test_report_character_sets_are_rows_with_copyable_code_points(tmp_path):
    import re
    from core.report_html import render
    fk.family(tmp_path)
    page = render(inspect(tmp_path))
    row = re.search(r"<div class='lrow [a-z]+' data-name=\"central european \(cp1250\)\".*?</div></div>", page, re.S)
    assert row, "cp1250 is partly covered by a Windows-1252 font and gets a row"
    text = row.group(0)
    assert "U+0151" in text and "ohungarumlaut" in text and "ő" in text
    assert "data-f='group:Windows'" in page and "data-f='script:Cyrl'" in page and "data-f='sort:size'" in page
    ascii_row = re.search(r"data-name=\"ascii\".*?<div class='lp'>(.*?)</div>", page, re.S).group(1)
    assert "100.0 %" in ascii_row and "(95/95)" in ascii_row


def test_workbook_coverage_sheet_lists_every_set(tmp_path):
    import io, openpyxl
    from core.report_xlsx import render as render_xlsx
    fk.family(tmp_path)
    result = inspect(tmp_path)
    rows = list(openpyxl.load_workbook(io.BytesIO(render_xlsx(result)))["Coverage"].iter_rows(min_row=1, values_only=True))
    assert rows[0][1] == "Character set" and rows[0][7] == "Code points to add"
    assert {r[1] for r in rows[1:]} == set(result["charsets"]["sets"])
    cp1250 = next(r for r in rows[1:] if r[1] == "Central European (cp1250)")
    assert cp1250[6] < 100 and "U+0151" in cp1250[7]


# ------------------------------------------------------------------ start-up: bundle, stages, site

def test_bundle_holds_the_core_and_the_cards_and_its_hash_follows_them(tmp_path):
    import shutil
    sys.path.insert(0, os.path.join(HERE, ".."))
    import bundle
    b = bundle.make()
    assert "__init__.py" in b["core"] and "checks/names.py" in b["core"] and "data/languages.json" in b["core"]
    assert "names.gdi_length.md" in b["rules"] and not any("__pycache__" in k for k in b["core"])
    assert bundle.make()["hash"] == b["hash"]
    # a copy with one word changed has another hash
    shutil.copytree(os.path.join(HERE, "..", "core"), tmp_path / "core", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(HERE, "..", "rules"), tmp_path / "rules")
    assert bundle.make(str(tmp_path))["hash"] == b["hash"]
    (tmp_path / "rules" / "names.gdi_length.md").write_text(b["rules"]["names.gdi_length.md"] + "\nedited\n")
    assert bundle.make(str(tmp_path))["hash"] != b["hash"]


def test_run_tells_its_stages(tmp_path):
    fk.family(tmp_path)
    paths = inventory.collect([str(tmp_path)])
    seen = []
    run(paths, ots={rel: "ok" for _, rel in paths}, stage=seen.append)
    assert seen == ["family and package checks", "collecting findings", "menu simulation", "character sets and languages"]
    seen.clear()
    run(paths, level="designer", ots={rel: "ok" for _, rel in paths}, stage=seen.append)
    assert "menu simulation" not in seen and seen[-1] == "character sets and languages"


def test_built_site_loads_in_one_request_and_has_what_the_page_installs(tmp_path):
    import json
    sys.path.insert(0, os.path.join(HERE, ".."))
    import build_site
    build_site.main(str(tmp_path))
    data = json.load(open(tmp_path / "core.bundle.json", encoding="utf-8"))
    sw = (tmp_path / "sw.js").read_text()
    assert f'VERSION = "{data["hash"]}"' in sw and "__VERSION__" not in sw
    assert not (tmp_path / "web" / "sw.js").exists(), "the worker script belongs at the site root, where its scope is the whole site"
    wheels = json.load(open(tmp_path / "wheels.json"))
    assert set(wheels) == {"openpyxl", "munkres"}
    assert all((tmp_path / "wheels" / f).exists() for names in wheels.values() for f in names)
    assert (tmp_path / "wheels" / wheels["munkres"][0]).stat().st_size > 1000
