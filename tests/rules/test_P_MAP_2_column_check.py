"""P-MAP-2: every mapped column is checked against its values. A warning never blocks; a missing required field does."""
import pytest

from tests.support.mapping import mapped, profiles
from wholecount.engine.mapping import ColumnRef, _profile, auto_map, check_field, process_blocks
from wholecount.engine.schema import default_schema


def check(field, values):
    return check_field(field, _profile(ColumnRef(0, "c"), values))


@pytest.mark.parametrize("field,values,status,reason", [
    ("Address_2", [""] * 5, "ok", "col_empty_ok"),
    ("Program", [""] * 5, "check", "col_empty"),
    ("Zip", ["11201", "", "", "", ""], "problem", "col_mostly_empty"),
    ("Address_1", ["03/04/2024"] * 4, "problem", "col_address1_dates"),
    ("Address_1", ["Apt 4", "Unit 2", "#3", "Fl 2", "12 Main St"], "problem", "col_address1_mostly_units"),
    ("Address_1", ["Main St", "Oak Ave", "Elm St", "1 Pine Rd"], "problem", "col_address1_not_streets"),
    ("Address_1", ["123", "456", "12 Main St", "789"], "problem", "col_address1_not_streets"),
    ("Zip", ["7030", "7302", "8540", "11201"], "check", "col_zip_lost_zero"),
    ("Zip", ["Brooklyn", "Queens", "11201", "x"], "problem", "col_zip_not_zips"),
    ("State", ["New York", "New Jersey", "NY"], "problem", "col_state_not_two_letters"),
    ("City", ["12 Main", "4 Oak", "Bronx"], "problem", "col_city_has_digits"),
    ("City", [f"Town{c}" for c in "abcdefghijklmnopqrstuvwxyz"] + ["Springfield"], "check", "col_city_many_values"),
    ("First_Name", ["12 Main St", "4 Oak Ave", "Ana"], "problem", "col_name_looks_like_address"),
    ("Last_Name", ["Lee2", "Cho3", "Ra"], "problem", "col_name_has_digits"),
    ("Last_Name", ["Lee"] * 11 + ["Cho"], "problem", "col_name_mostly_one_value"),
    ("Middle_Initial", ["Anne", "Marie", "Lou"], "check", "col_middle_full_names"),
    ("Client_ID", ["A1", "A1", "A1", "B2"], "problem", "col_id_repeats"),
    ("Program", ["03/04/2024", "4/5/2023", "Youth"], "problem", "col_program_looks_like_dates"),
    ("Program", ["101", "102", "103", "Youth"], "problem", "col_program_looks_like_codes"),
    ("Address_2", ["12 Main St", "4 Oak Ave", "9 Elm St", "1 Pine Rd", "3 Ash St", "Apt 2"], "check", "col_address2_mostly_streets"),
    ("Address_2", ["garden", "office", "shed", "barn", "porch", "attic"], "check", "col_address2_not_units"),
    ("Program", ["Youth"] + [""] * 9, "check", "col_low_fill"),
    ("Zip", ["11201", "10027"], "ok", "col_ok"),
])
def test_each_check(field, values, status, reason):
    r = check(field, values)
    assert (r.status, r.reason_id) == (status, reason)


def test_better_column_suggests_zip_when_the_mapped_column_is_blank():
    values = {"Zip Code": [""] * 8, "Zip": ["11201", "10027", "10458", "11375", "11201", "10027", "10458", "11375"]}
    m = mapped(["Zip Code", "Zip"], values)
    m2 = m.with_choice("Zip", next(c.column for c in profiles(["Zip Code", "Zip"], values) if c.column.name == "Zip Code"))
    from wholecount.engine.mapping import check_mapping
    checked = check_mapping(default_schema(), m2, profiles(["Zip Code", "Zip"], values))
    assert checked.checks["Zip"].status == "problem" and checked.checks["Zip"].better.name == "Zip"


def test_warning_never_blocks_but_a_missing_name_does():
    s = default_schema()
    p = profiles(["Last Name", "Client ID", "Zip"], {"Zip": ["x", "y", "z"]})
    m = auto_map(s, p, "t")
    blocks = process_blocks(s, {"t": m}, (), {"t": p})
    assert [(b.field, b.kind) for b in blocks] == [("First_Name", "missing_required")]


def test_a_table_with_no_address_column_still_runs():
    s = default_schema()
    p = profiles(["First Name", "Last Name", "Client ID"])
    assert process_blocks(s, {"t": auto_map(s, p, "t")}, (), {"t": p}) == []


def test_an_open_question_counts_as_no_column():
    s = default_schema()
    p = profiles(["Surname", "Family", "First Name", "ID"])
    blocks = process_blocks(s, {"t": auto_map(s, p, "t")}, (), {"t": p})
    assert [(b.field, b.kind) for b in blocks] == [("Last_Name", "missing_required")]
