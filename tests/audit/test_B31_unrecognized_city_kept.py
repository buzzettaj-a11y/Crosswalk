"""B-31 (High): a typed city that wasn't recognized was overwritten by the ZIP's borough."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("city", ["Yonkers", "Hoboken"])
def test_B31_kept_with_a_suggestion(city):
    r = std(City=city, Zip="10001")
    assert r.value("City") == city and ids(r) == ["city_not_recognized"] and r.values["City"].suggestions == ("New York",)
    assert r.count_status.counted and r.location.reason == "address_problem" and r.location.problems == ("city_not_recognized",)


def test_B31_misspelling_suggests_the_zips_borough():
    assert std(City="Brooklin", Zip="11201").values["City"].suggestions == ("Brooklyn",)
