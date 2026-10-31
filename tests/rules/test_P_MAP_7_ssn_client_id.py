"""P-MAP-7 and fix plan 4.1: a Client_ID column of mostly SSN-shaped values blocks Process."""
import pytest

from tests.support.mapping import profiles
from wholecount import copy
from wholecount.engine.defaults import SourceDefault
from wholecount.engine.mapping import auto_map, process_blocks
from wholecount.engine.schema import default_schema

S = default_schema()
BASE = ["First Name", "Last Name"]


def blocks(cols, values, defaults=(), choose=None):
    p = profiles(cols, values)
    m = auto_map(S, p, "t")
    if choose:
        m = m.with_choice(*choose(p))
    return process_blocks(S, {"t": m}, defaults, {"t": p})


def ssn_values(n_ssn, n_other, rotate=0):
    v = ["123-45-6789"] * n_ssn + [f"C{i}" for i in range(n_other)]
    return v[rotate:] + v[:rotate]


@pytest.mark.parametrize("rotate", [0, 2, 4])
def test_sixty_percent_blocks_naming_table_and_field_only(rotate):
    b = blocks(BASE + ["Client ID"], {"Client ID": ssn_values(3, 2, rotate)})
    assert [(x.table_key, x.field, x.kind) for x in b] == [("t", "Client_ID", "ssn_shaped_id")]
    assert "123-45" not in repr(b)


def test_exactly_half_does_not_block():
    assert blocks(BASE + ["Client ID"], {"Client ID": ssn_values(2, 2)}) == []


def test_a_default_does_not_clear_it():
    b = blocks(BASE + ["Client ID"], {"Client ID": ssn_values(3, 2)}, [SourceDefault("t", "Client_ID", "X")])
    assert [x.kind for x in b] == ["ssn_shaped_id"]


def test_remapping_clears_it():
    cols = BASE + ["Client ID", "Member Number", "DOB"]
    vals = {"Client ID": ssn_values(3, 2), "Member Number": ["M1", "M2", "M3", "M4", "M5"]}
    b = blocks(cols, vals, choose=lambda p: ("Client_ID", next(x.column for x in p if x.column.name == "Member Number")))
    assert b == []


def test_dropping_the_column_clears_it():
    assert blocks(BASE + ["DOB"], {"DOB": ["1990-01-01"] * 5}) == []


def test_the_same_digits_in_program_never_block():
    cols = BASE + ["ID", "Program"]
    vals = {"ID": ["C1", "C2", "C3", "C4", "C5"], "Program": ssn_values(3, 2)}
    assert blocks(cols, vals) == []


def test_copy():
    assert copy.get("map.block.ssn_shaped_id") == ("These identifiers look like Social Security numbers. Map a different identifier, "
                                                   "or drop this column.")
