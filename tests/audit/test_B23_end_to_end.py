"""B-23, the whole chain: propose, apply and map on a file with a caseworker's name beside the client's own columns."""
from tests.support.tables import table
from wholecount.engine.mapping import auto_map, profile_columns
from wholecount.engine.prepare.steps import Step, apply_steps, propose_steps
from wholecount.engine.schema import default_schema

S = default_schema()


def test_B23_end_to_end():
    t = table(["Client ID", "Caseworker Name", "First Name", "Last Name"], [
        ["1", "Lee, Ana", "Ben", "Cho"], ["2", "Ra, Cy", "Di", "Fox"], ["3", "Lee, Ana", "Ed", "Gu"]])
    steps = propose_steps(t, auto_map(S, profile_columns(t), "t"))
    assert steps == []
    forced = apply_steps(t, [Step("x", "split_name", {"column": "Caseworker Name"})])
    m = auto_map(S, profile_columns(t, forced.column_refs()), "t").as_names()
    assert m["First_Name"] == "First Name" and m["Last_Name"] == "Last Name"
