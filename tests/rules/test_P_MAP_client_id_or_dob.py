"""SPEC 4.1: Client_ID's column requirement is met when a table maps either Client_ID or Date_of_Birth."""
from tests.support.mapping import profiles
from wholecount.engine.mapping import auto_map, process_blocks
from wholecount.engine.schema import default_schema

S = default_schema()


def blocks(cols, schema=S):
    p = profiles(cols)
    return [(b.field, b.kind, b.also) for b in process_blocks(schema, {"t": auto_map(schema, p, "t")}, (), {"t": p})]


def test_only_dob_mapped_is_not_blocked():
    assert blocks(["First Name", "Last Name", "DOB"]) == []


def test_neither_blocks_once_naming_both():
    assert blocks(["First Name", "Last Name"]) == [("Client_ID", "missing_required", "Date_of_Birth")]


def test_client_id_optional_for_the_batch():
    assert blocks(["First Name", "Last Name"], S.with_required("Client_ID", False)) == []


def test_dob_disabled_no_longer_meets_it():
    assert blocks(["First Name", "Last Name", "DOB"], S.with_enabled("Date_of_Birth", False)) == [
        ("Client_ID", "missing_required", "Date_of_Birth")]
