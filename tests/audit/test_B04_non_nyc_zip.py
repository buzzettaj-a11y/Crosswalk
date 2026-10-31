"""B-04 (High): a NYC borough with a non-NYC ZIP was clean."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("zip_", ["07030", "12345", "99999", "00000"])
def test_B04_borough_with_outside_zip(zip_):
    r = std(City="Brooklyn", State="NY", Zip=zip_)
    assert r.count_status.counted and r.location.reason == "outside_nyc" and "city_zip_disagree" in ids(r)
