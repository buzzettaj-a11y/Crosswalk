"""B-47: the old default copy rule grouped on name and ZIP alone. A name needs a DOB or a full address with it (P-DUP-2)."""
import pytest

from tests.fixtures.people.builders import crow
from wholecount.engine.copies import CopyRule, TableInfo, find_copies

T = {"t": TableInfo(False, "S")}


def test_same_name_and_zip_is_not_a_copy():
    rows = [crow("r1", "t", "S", "1", "Maria", "Garcia", "", "1 Oak St", "11201"),
            crow("r2", "t", "S", "2", "Maria", "Garcia", "", "9 Pine St", "11201")]
    assert find_copies(rows, T) == []


def test_same_name_and_address_is_possible():
    rows = [crow("r1", "t", "S", "1", "Maria", "Garcia", "", "1 Oak St", "11201"),
            crow("r2", "t", "S", "2", "Maria", "Garcia", "", "1 Oak St", "11201")]
    assert [g.kind for g in find_copies(rows, T)] == ["possible"]


def test_a_name_and_zip_rule_is_refused():
    with pytest.raises(ValueError):
        CopyRule(fields=("surname", "given", "zip"))


def test_different_programs_never_group():
    rows = [crow("r1", "t", "S", "", "Maria", "Garcia", "", "1 Oak St", "11201", "Housing"),
            crow("r2", "t", "S", "", "Maria", "Garcia", "", "1 Oak St", "11201", "Youth")]
    assert find_copies(rows, T) == []
