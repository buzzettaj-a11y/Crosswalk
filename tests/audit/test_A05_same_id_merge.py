"""A-05: two household members under one Client ID were silently counted as one person. They're never joined without asking."""
import csv

from tests.conftest import ROOT
from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import ApprovedAsEntered, TableInfo, apply_copy_decision, find_copies, key_modes
from wholecount.engine.identity import resolve


def rows():
    with open(ROOT / "docs" / "audit" / "A-fixtures" / "household.csv", newline="", encoding="utf-8") as f:
        recs = [r for r in csv.DictReader(f) if r["Client_ID"] in ("H100", "H200")]
    return [crow(f"r{i}", "h", "household", r["Client_ID"], r["First_Name"], r["Last_Name"], "", r["Address_1"], r["Zip"],
                 r["Program"]) for i, r in enumerate(recs)]


def test_never_joined_without_asking():
    rs = rows()
    groups = find_copies(rs, {"h": TableInfo(False, "household")})
    (g,) = groups
    assert g.kind == "same_id_different" and len(g.members) == 2
    out = apply_copy_decision(g, ApprovedAsEntered())
    assert set(out.counted) == set(g.members)
    modes = key_modes(groups, {g.group_id: ApprovedAsEntered()}, rows=rs)
    r = resolve([to_person(c, modes) for c in rs])
    assert r.auto_joins == () and (r.settled, r.low) == (3, 2)
