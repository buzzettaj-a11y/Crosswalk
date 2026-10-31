"""B-25 (Medium): real names Na, Nan and None were blanked as null markers."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.standardize.model import count_status_for


@pytest.mark.parametrize("name", ["Na", "Nan", "None", "Nil"])
def test_B25_kept_with_a_soft_reason(name):
    r = std(First_Name=name)
    assert r.value("First_Name") == name and ids(r) == ["name_may_be_placeholder"]
    assert r.count_status.value == "counted_passed"
    assert count_status_for(r, approved=True).value == "counted_approved" and r.value("First_Name") == name


@pytest.mark.parametrize("name", ["NULL", "-"])
def test_B25_null_and_dash_still_blank(name):
    assert "name_missing" in ids(std(Last_Name=name))
