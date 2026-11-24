"""The rule for the full name (ID 4), written as a test before the check exists.

    base  = ID 16, else ID 1          (OpenType spec: without ID 16, ID 1 is the typographic family)
    style = ID 17, else ID 2
    expected = base + " " + style      compared with ID 4

    match     ID 4 is exactly the expected string
    harmless  the same words with another case or spacing, or "Regular" left out (the spec says it is generally
              omitted on a non-regular font whose ID 2 is Regular, and is silent about ordinary Regular fonts)
    confirm   other words or another order: the spec allows "a similar human-readable variant", so a person decides
    None      ID 4 or the style/family is missing: names.required reports that

When ID 16/17 exist, ID 1 + ID 2 are NOT compared with ID 4: the spec's own examples (Minion Pro SmBd, Adobe Caslon
Pro Semibold with ID 2 = Bold) have an ID 1 + ID 2 that differs from the full name on purpose.

The function to write: core.checks.names.full_name_verdict(names) -> (verdict, expected), names being {"1": ..., ...}.
Until it exists, the tests are skipped, so the suite stays green.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.checks import names as names_module  # noqa: E402

verdict = getattr(names_module, "full_name_verdict", None)
pytestmark = pytest.mark.skipif(verdict is None, reason="names.full_name_verdict is not written yet")


def n(**ids):
    return {k.lstrip("i"): v for k, v in ids.items()}


CASES = [
    # (what it shows, names, expected verdict, expected string)
    ("typographic pair", n(i1="Acme Sans Light", i2="Italic", i4="Acme Sans Light Italic", i16="Acme Sans", i17="Light Italic"),
     "match", "Acme Sans Light Italic"),
    ("no ID 16/17: ID 1 + ID 2", n(i1="Acme Sans", i2="Bold", i4="Acme Sans Bold"), "match", "Acme Sans Bold"),
    ("Regular written out", n(i1="Acme Sans", i2="Regular", i4="Acme Sans Regular"), "match", "Acme Sans Regular"),
    ("Regular left out of a regular font", n(i1="Acme Sans", i2="Regular", i4="Acme Sans"), "harmless", "Acme Sans Regular"),
    ("Regular left out of Arial Black (the spec's example)", n(i1="Arial Black", i2="Regular", i4="Arial Black"),
     "harmless", "Arial Black Regular"),
    ("ID 1 abbreviated, ID 16/17 carry the real names (Minion Pro SmBd)",
     n(i1="Minion Pro SmBd", i2="Regular", i4="Minion Pro Semibold", i16="Minion Pro", i17="Semibold"),
     "match", "Minion Pro Semibold"),
    ("ID 2 linked as Bold for a Semibold (Adobe Caslon Pro)",
     n(i1="Adobe Caslon Pro", i2="Bold", i4="Adobe Caslon Pro Semibold", i16="Adobe Caslon Pro", i17="Semibold"),
     "match", "Adobe Caslon Pro Semibold"),
    ("Regular left out of a longer style (Volvo Centum Dark Regular)",
     n(i1="Acme Sans Dark", i2="Regular", i4="Acme Sans Dark", i16="Acme Sans", i17="Dark Regular"), "harmless", "Acme Sans Dark Regular"),
    ("case and spaces differ", n(i1="Acme Sans", i2="Bold", i4="acme  sans bold"), "harmless", "Acme Sans Bold"),
    ("ID 16 present, ID 17 missing: ID 2 is the style", n(i1="Acme Sans", i2="Bold", i4="Acme Sans Bold", i16="Acme Sans"),
     "match", "Acme Sans Bold"),
    ("another word", n(i1="Acme Sans", i2="Bold", i4="Acme Sans Black"), "confirm", "Acme Sans Bold"),
    ("another order", n(i1="Acme Sans Light", i2="Italic", i4="Acme Sans Italic Light", i16="Acme Sans", i17="Light Italic"),
     "confirm", "Acme Sans Light Italic"),
    ("family left out", n(i1="Acme Sans", i2="Bold", i4="Bold"), "confirm", "Acme Sans Bold"),
]


@pytest.mark.parametrize("what,names,want,expected", CASES, ids=[c[0] for c in CASES])
def test_full_name_verdict(what, names, want, expected):
    got, string = verdict(names)
    assert (got, string) == (want, expected)


def test_missing_names_are_not_judged_here():
    assert verdict(n(i1="Acme Sans", i2="Bold"))[0] is None      # no ID 4: names.required reports it
    assert verdict(n(i4="Acme Sans Bold"))[0] is None            # no family or style to build the string from


def test_id1_and_id2_are_not_compared_when_typographic_names_exist():
    names = n(i1="Minion Pro SmBd", i2="Regular", i4="Minion Pro Semibold", i16="Minion Pro", i17="Semibold")
    assert verdict(names)[0] == "match"
