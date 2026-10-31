"""P-STD-1: names are re-cased only when all upper or all lower, digits are flagged, and the middle initial is reduced."""
import pytest

from tests.support.std import ids, std


def test_recase_and_note():
    r = std(First_Name="JOHN", Last_Name="smith")
    assert (r.value("First_Name"), r.value("Last_Name")) == ("John", "Smith")
    assert [n.reason_id for n in r.notes] == ["name_recased", "name_recased"]


def test_mixed_case_kept():
    assert std(Last_Name="McDonald").value("Last_Name") == "McDonald" and std(Last_Name="McDonald").notes == ()


@pytest.mark.parametrize("name,flag", [("J0hn", True), ("3rd", True), ("Mary-Kate", False), ("St. John", False), ("Smith III", False)])
def test_digits(name, flag):
    assert ("digits_in_name" in ids(std(First_Name=name))) == flag


@pytest.mark.parametrize("raw,out,note", [("Marie", "M", "middle_initial_reduced"), ("NMI", "", "middle_initial_dropped"), ("J", "J", None)])
def test_middle_initial(raw, out, note):
    r = std(Middle_Initial=raw)
    assert r.value("Middle_Initial") == out and [n.reason_id for n in r.notes if n.field == "Middle_Initial"] == ([note] if note else [])


def test_spaces_collapse():
    assert std(First_Name="Mary  Beth").value("First_Name") == "Mary Beth"
