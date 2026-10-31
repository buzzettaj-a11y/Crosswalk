"""B-17: the old fallback fuzzy-matched a near address and gave a wrong building's point and districts. Exact only now (P-GEO-3).

Each ask runs against a reference holding only its near neighbor, as the audit script did, because 1 Main St, 1 Avenue U and
40 W 100 St are themselves rows of the audit's reference file. The asks with no near row in the file run against the whole file.
"""
import pytest

from tests.support.geo import FIX, ref_b17, reference_of

ROWS = {tuple(l.split(",")[:3]): l.split(",") for l in (FIX / "refdata_b17.csv").read_text().splitlines()[1:]}


def only(house, street, zip5):
    r = ROWS[(house, street, zip5)]
    return reference_of([r])


CASES = [
    ("111", "Main St", "11201", lambda: only("11", "Main St", "11201")),
    ("1", "Main St", "11201", lambda: only("11", "Main St", "11201")),
    ("1", "Avenue U", "11223", lambda: only("1", "Avenue V", "11223")),
    ("40", "W 100 St", "10025", lambda: only("100", "W 40 St", "10025")),
    ("100", "W 100 St", "10011", lambda: only("100", "W 10 St", "10011")),
    ("12", "W 40 St", "10025", ref_b17),
    ("45", "Beach 90 St", "11693", ref_b17),
    ("111", "Main St", "11201", ref_b17),
]


@pytest.mark.parametrize("house,street,where,make", CASES)
def test_near_addresses_are_not_placed(house, street, where, make):
    r = make().lookup(house, street, where)
    assert (r.confidence, r.reason) == ("not_placed", "not_found")
    assert r.latitude is None and r.longitude is None and r.districts is None


def test_exact_rows_still_place_and_districts_follow_the_address():
    ref = ref_b17()
    a, b = ref.lookup("1", "Main St", "11201"), ref.lookup("11", "Main St", "11201")
    assert (a.latitude, a.longitude) == (40.7, -73.99) and (b.latitude, b.longitude) == (40.704, -73.98)


def test_suggestions_are_for_a_person_only():
    ref = ref_b17()
    assert [(s.house_number, s.street) for s in ref.suggest("123", "Fultin St", "11201")] == [("123", "Fulton St")]
    assert ref.suggest("123", "Fultin St", "11201")[0].ratio == pytest.approx(0.833, abs=0.001)
    assert ref.suggest("111", "Main St", "11201") == ()
    assert ref.suggest("5", "Beach 19 St", "11691") == ()
    assert ref.suggest("123", "Fulton Pl", "11201") == ()
