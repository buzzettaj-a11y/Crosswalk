"""P-PREP-5: the calculated ZIP step, its note column and its counts."""
from tests.support.tables import table
from tests.support.zips import DictResolver
from wholecount.engine.prepare.steps import Step, apply_steps

T = table(["Client_ID", "Street", "City", "Zip"], [
    ["1", "209 Joralemon St", "Brooklyn", ""], ["2", "1 Nowhere Pl", "Brooklyn", "112019"], ["3", "60 Centre St", "New York", "10007"],
    ["4", "", "Queens", ""],
])
R = DictResolver({("209 Joralemon St", "Brooklyn"): "11201"})
STEP = Step("z", "calc_zip", {"street_col": "Street", "city_col": "City", "zip_col": "Zip", "mode": "blanks"})


def test_blanks_mode():
    p = apply_steps(T, [STEP], R)
    assert p.values("Zip_calculated") == ["11201", "", "10007", ""]
    assert p.values("Zip_calculated_note") == ["zip_found", "zip_not_worked_out", "zip_kept", "no_street"]
    assert p.results[0].counts == {"found": 1, "kept": 1, "not_worked_out": 1} and not p.results[0].amber


def test_all_mode_looks_everything_up():
    from dataclasses import replace
    p = apply_steps(T, [replace(STEP, params={**STEP.params, "mode": "all"})], R)
    assert p.values("Zip_calculated")[2] == "" and p.values("Zip_calculated_note")[2] == "zip_not_worked_out"


def test_no_resolver_is_amber_and_writes_nothing():
    p = apply_steps(T, [STEP])
    r = p.results[0]
    assert r.amber and r.amber_reason == "no_lookup_available"
    assert p.values("Zip_calculated_note")[0] == "no_lookup_available" and p.values("Zip_calculated")[0] == ""


def test_the_mapper_takes_the_calculated_zip():
    from tests.support.mapping import mapped
    from wholecount.engine.mapping import profile_columns, auto_map
    from wholecount.engine.schema import default_schema
    p = apply_steps(T, [STEP], R)
    s = default_schema()
    m = auto_map(s, profile_columns(T, p.column_refs()), "t")
    assert m.as_names()["Zip"] == "Zip_calculated"
