"""B-15 (High): future dates were accepted as dates of birth, up to 2100."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("dob", ["2026-10-30", "1911-10-30"])
def test_B15_pass(dob):
    assert ids(std(Date_of_Birth=dob)) == []


@pytest.mark.parametrize("dob", ["2026-10-31", "2027-01-01", "2045-01-02", "2099-12-31", "2100-01-01", "03/04/2050", "1899-12-31"])
def test_B15_out_of_range(dob):
    assert ids(std(Date_of_Birth=dob)) == ["dob_out_of_range"]


@pytest.mark.parametrize("dob", ["1900-01-01", "1910-10-30"])
def test_B15_over_115(dob):
    assert ids(std(Date_of_Birth=dob)) == ["dob_age_over_115"]


def test_B15_counting():
    assert std(Date_of_Birth="2030-01-01").count_status.counted
    r = std(Date_of_Birth="2030-01-01", Client_ID="")
    assert set(ids(r)) == {"dob_out_of_range", "no_identifier"} and r.count_status.value == "not_counted_yet"
    r = std(Date_of_Birth="1900-01-01", Client_ID="")
    assert ids(r) == ["dob_age_over_115"] and r.count_status.counted
