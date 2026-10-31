"""Cause kinds (REV-2): fill_from_street, mapping_diagnosis, no_address, copies, same_id, settled, and the cross-file note."""
import pytest

from tests.support.session import base
from wholecount import copy
from wholecount.engine.mapping import ColumnRef, auto_map, profile_columns
from wholecount.engine.review import Cause, diagnose_mapping, people_in_other_files
from wholecount.engine.schema import default_schema
from wholecount.session.runner import causes_for


def test_kinds_from_the_fixture(tmp_path):
    s = base(tmp_path)
    kinds = {c.cause_id: c.kind for c in causes_for(s.results)}
    assert kinds["address_part_missing"] == "fill_from_street" and kinds["copies_identical"] == "copies"
    assert kinds["same_id_conflict"] == "same_id" and kinds["summary_row"] == "settled"


@pytest.mark.claim("CL-REV-03")
def test_people_in_other_files(tmp_path):
    r = base(tmp_path).results
    counted = [k for k, o in r.outcomes.items() if o.counted]
    assert people_in_other_files(r.identity.master_of_record, r.file_of_record, counted) == 1
    assert copy.get("review.cross_file_note", count=1).startswith("1 people")


@pytest.mark.claim("CL-REV-04")
def test_mapping_diagnosis_names_columns_only():
    from tests.support.tables import table
    t = table(["Name", "REGION", "BOROUGH"], [["a", "", "Brooklyn"], ["b", "", "Queens"], ["c", "", "Bronx"], ["d", "", "Brooklyn"]])
    profiles = profile_columns(t)
    m = auto_map(default_schema(), profiles, t.key)
    region = next(p.column for p in profiles if p.column.name == "REGION")
    m = m.with_choice("City", region)
    cause = Cause("city_not_recognized", 4, "x", (), False, "location", "other", ("k0", "k1", "k2", "k3"), "City")
    d = diagnose_mapping(cause, m, profiles, {f"k{i}": (t.key, i) for i in range(4)})
    assert d is not None and (d.column_now, d.column_better, d.rows_fixed) == ("REGION", "BOROUGH", 4)
    text = copy.get("review.mapping_diagnosis", field=d.field, column_now=d.column_now, column_better=d.column_better, count=d.rows_fixed)
    assert "REGION" in text and "BOROUGH" in text and "Brooklyn" not in text
