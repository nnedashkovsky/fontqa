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
ALLOWED_ON_CLEAN = {("vf.var_tables", "HVAR without side-bearing maps")}
NEED_INPUT = {"external.fontbakery", "release.font_json"}


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
    assert "Partial run: 6 of 55 checks" in render(result)
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
