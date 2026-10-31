"""Every case in tests/fixtures/geo/fake_queries.csv against the fake gazetteer."""
import csv

import pytest

from tests.support.geo import FIX, fake

CASES = list(csv.DictReader((FIX / "fake_queries.csv").open(encoding="utf-8")))


@pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
def test_fake_backend_fixture(case):
    r = fake().lookup(case["house_number"], case["street"], case["borough_or_zip"])
    assert (r.confidence, r.reason) == (case["expect_confidence"], case["expect_reason"])
    if case["expect_lat"]:
        assert (r.latitude, r.longitude) == (float(case["expect_lat"]), float(case["expect_lon"]))
        assert f"{r.districts.senate}/{r.districts.assembly}/{r.districts.council}" == case["expect_districts"]
    else:
        assert r.latitude is None and r.longitude is None and r.districts is None
