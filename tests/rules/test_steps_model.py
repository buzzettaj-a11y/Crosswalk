"""The step model: order, remove and restore, amber rows, unique names, no source change, and proposals that skip other people."""
from tests.support.tables import table
from wholecount.engine.mapping import auto_map, profile_columns
from wholecount.engine.prepare.steps import Step, apply_steps, propose_steps, restore_step, source_cells_changed, without_step
from wholecount.engine.schema import default_schema

S = default_schema()
T = table(["Client_ID", "Name", "Full Address"], [
    ["1", "Lee, Ana M", "12 Main St Apt 3 Brooklyn NY 11201"], ["2", "Cho, Ben", "45 Oak St, Queens, NY 11375"],
    ["3", "Ra, Cy", "60 Centre St New York NY 10007"],
])


def test_steps_run_in_order_and_read_earlier_outputs():
    steps = [Step("a", "split_name", {"column": "Name"}), Step("b", "clean", {"columns": ["Name_last"], "case": "upper"})]
    p = apply_steps(T, steps)
    assert p.values("Name_last_clean") == ["LEE", "CHO", "RA"]


def test_remove_and_restore():
    steps = [Step("a", "split_name", {"column": "Name"})]
    off = without_step(steps, "a")
    assert off[0].removed and apply_steps(T, off).columns == []
    assert apply_steps(T, restore_step(off, "a")).values("Name_first") == ["Ana", "Ben", "Cy"]


def test_source_cells_never_change():
    before = [list(r) for r in T.rows]
    apply_steps(T, [Step("a", "split_name", {"column": "Name"}), Step("b", "split_address", {"column": "Full Address"}),
                    Step("c", "clean", {"columns": ["Name", "Full Address"], "case": "upper", "strip_junk": True})])
    assert source_cells_changed(before, T) == 0


def test_column_refs_are_derived_with_their_source_and_kind():
    p = apply_steps(T, [Step("a", "split_name", {"column": "Name"})])
    refs = [r for r, _ in p.column_refs()]
    assert all(r.derived and r.derived_from == "Name" and r.derived_kind == "split" for r in refs)
    assert refs[0].index == 3


def test_proposals_for_the_clients_own_columns():
    m = auto_map(S, profile_columns(T), "t")
    steps = propose_steps(T, m)
    assert [(s.kind, s.params["column"], s.origin) for s in steps] == [("split_address", "Full Address", "proposed"),
                                                                       ("split_name", "Name", "proposed")]


def test_proposals_skip_caseworker_and_employer_columns():
    t = table(["Client_ID", "Caseworker Name", "Employer Address"], [
        ["1", "Lee, Ana", "12 Main St Apt 3 Brooklyn NY 11201"], ["2", "Cho, Ben", "45 Oak St, Queens, NY 11375"]])
    assert propose_steps(t, auto_map(S, profile_columns(t), "t")) == []


def test_a_unit_line_is_left_alone():
    t = table(["Client_ID", "Street", "Address 2"], [["1", "12 Main St", "Apt 3"], ["2", "45 Oak St", "Apt 4B"], ["3", "1 Elm St", "#2"]])
    assert propose_steps(t, auto_map(S, profile_columns(t), "t")) == []
