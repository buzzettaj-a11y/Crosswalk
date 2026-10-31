"""B-41 (Low): Marble Hill gave a false City/ZIP conflict."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("city", ["Manhattan", "Bronx"])
def test_B41_both_boroughs_agree_with_10463(city):
    r = std(City=city, Zip="10463")
    assert ids(r) == [] and r.location.kind == "to_place"


def test_B41_brooklyn_with_10463_disagrees():
    r = std(City="Brooklyn", Zip="10463")
    assert ids(r) == ["city_zip_disagree"] and r.count_status.counted
