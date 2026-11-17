"""Check registry: what a check is, what it returns, how files are grouped.

A check is a generator function plus metadata. The metadata is what the report
prints around a finding — category, classification, basis, fix direction, the
symptoms users would see — so a check author writes it once, next to the code,
in English (the report language).

Scopes decide what the function receives:
  file     one FontView                     (names, metrics of a single font)
  outline  one FontView per distinct outline table (App/Desktop/Web copies of
           one style share outlines; the finding still lists every copy)
  family   a list of FontViews of one family in one lineage (consistency)
  package  every FontView of the delivery    (uniqueness across families)

A check yields Hit objects. Hits with the same check and `key` become one issue,
however many files they come from; that is how 48 files with one problem make
one row, as in RT's reports. Defaults for action, severity and judgment come
from the metadata; a hit may override them when one case is worse than another.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

ACTIONS = ("fix", "confirm", "ok")
SEVERITIES = ("high", "medium", "low")
CATEGORIES = {
    "A": "Environment and installation",
    "C": "Character set, glyphs, widths",
    "D": "OpenType layout",
    "E": "Tool inspection",
    "F": "Table values and names",
    "G": "Variable fonts",
    "R": "Release readiness",
}


@dataclass
class Hit:
    key: str
    summary: str
    measured: object = None
    expected: object = None
    glyphs: list = field(default_factory=list)
    files: Optional[list] = None     # family/package checks name their files
    action: Optional[str] = None
    severity: Optional[str] = None
    judgment: Optional[str] = None


@dataclass
class Check:
    id: str
    category: str
    title: str
    classification: str
    scope: str
    fn: Callable
    what: str
    basis: str
    fix: str
    action: str = "fix"
    severity: str = "medium"
    judgment: str = "×"
    symptoms: tuple = ()
    applies: Optional[Callable] = None
    profiles: tuple = ("release",)
    requires: tuple = ()             # context inputs without which the check is "not performed"

    def applicable(self, view):
        return view.ok and (self.applies is None or self.applies(view))

    @property
    def level(self):
        return "designer" if self.id in DESIGNER else "engineer"


# Checks a type designer runs: what concerns the drawing (core/levels.py).
# Everything else is file-level and runs at the engineer level only.
DESIGNER = frozenset({
    # character set and family
    "charset.family_same", "charset.store_minimum", "glyphs.empty_mapped", "glyphs.notdef",
    # outlines
    "outline.extrema", "outline.zero_length", "outline.fractional",
    # metrics
    "glyphs.spaces", "glyphs.tabular", "glyphs.mark_widths", "widths.near_equal",
    "metrics.x_cap_height", "metrics.win_clipping", "metrics.family_vertical",
    # kerning and OpenType features
    "layout.kern_shadowed", "layout.unreachable", "layout.aalt", "layout.marks",
    # variable fonts: the drawing side
    "vf.interpolation", "vf.vs_static",
})


# Named selections of checks: id prefixes, run inside the chosen level. `all` runs everything the level has.
PRESETS = {
    "all": {"title": "Everything", "prefixes": None,
            "about": "every check of the chosen level"},
    "differences": {"title": "Differences between styles",
                    "prefixes": ["charset.family_same", "widths.near_equal", "metrics.family_vertical",
                                 "names.family_consistent", "lineage.copies_agree", "vf.vs_static"],
                    "about": "checks that compare fonts with each other: character set, widths, vertical metrics, "
                             "family-wide names, copies in App/Desktop/Web, variable against static"},
    "names": {"title": "Names", "prefixes": ["names.", "tables.meta"], "about": "name table and family naming"},
    "tables": {"title": "Table values", "prefixes": ["os2.", "post.", "tables.hinting"],
               "about": "OS/2, post and hinting values"},
    "metrics": {"title": "Metrics", "prefixes": ["metrics."], "about": "vertical metrics and line spacing"},
    "glyphs": {"title": "Character set and glyphs", "prefixes": ["charset.", "glyphs.", "widths."],
               "about": "coverage, empty glyphs, spaces, tabular figures, widths"},
    "outlines": {"title": "Outlines", "prefixes": ["outline."], "about": "extremes, zero-length segments, coordinates"},
    "layout": {"title": "OpenType layout", "prefixes": ["layout."], "about": "scripts, kerning, alternates, marks"},
    "variable": {"title": "Variable fonts", "prefixes": ["vf."], "about": "instances, STAT, masters, against statics"},
    "lineage": {"title": "App / Desktop / Web copies", "prefixes": ["lineage."], "about": "copies of one style agree"},
    "release": {"title": "Release", "prefixes": ["release."], "about": "formats, file names, credits, version"},
    "validators": {"title": "Validators", "prefixes": ["external."], "about": "OTS and Font Bakery"},
}


def preset_prefixes(name):
    """Id prefixes of a preset (None = all). Unknown names raise, so a typo never runs a full check silently."""
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r}; known: {', '.join(PRESETS)}")
    return PRESETS[name]["prefixes"]


def catalog(registry=None):
    """What the page needs to offer a choice of checks."""
    return [{"id": c.id, "title": c.title, "category": c.category, "level": c.level}
            for c in sorted(registry or REGISTRY, key=lambda c: (c.category, c.id))]


def in_level(check, level):
    """Engineer runs everything; designer runs the drawing checks."""
    return level != "designer" or check.level == "designer"


REGISTRY = []


def check(**meta):
    def register(fn):
        REGISTRY.append(Check(fn=fn, **meta))
        return fn
    return register


# ------------------------------------------------------------- predicates

def installable(v):
    """Fonts a user installs: names drive menus. Web fonts are loaded by CSS."""
    return v.lineage != "Web" and v.fmt in ("OTF", "TTF")


def sfnt(v):
    return v.fmt in ("OTF", "TTF", "WOFF", "WOFF2")


def static(v):
    return not v.variable


# ------------------------------------------------------------- grouping

def families(views):
    """Groups for consistency checks: same family name, same lineage, static vs VF."""
    groups = {}
    for v in views:
        if v.ok:
            groups.setdefault((v.family, v.lineage or "", v.variable), []).append(v)
    return [g for _, g in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))]


def files_of(views):
    return [v.rel for v in views]


def load_all():
    """Import the check modules (registration happens on import)."""
    from . import names, metrics, charset, outline, layout, external, release, variable, lineage  # noqa: F401
    # registration order depends on which module was imported first (core.inspection imports
    # charset on its own); sort, so the terminal and the browser list the checks the same way
    REGISTRY.sort(key=lambda c: (c.category, c.id))
    unknown = DESIGNER - {c.id for c in REGISTRY}
    assert not unknown, f"DESIGNER lists unknown checks: {sorted(unknown)}"
    return REGISTRY
