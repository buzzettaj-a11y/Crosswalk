"""Properties of placing (H3, P-GEO-7, P-GEO-5, MAP-1): the offset's range and determinism, row independence, holes, the address
key's stability, and small-cell blanking."""
import hashlib
import hmac

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.geo import NO_EXTRAS, reference_of, row
from wholecount.engine.addresskey import address_key
from wholecount.engine.geo.districts import polygon_contains, ring_contains
from wholecount.engine.geo.mapdata import MapEntry, build_map_counts
from wholecount.engine.geo.offset import PrivacyOffset, haversine_ft
from wholecount.engine.geo.place import place_rows
from wholecount.engine.geo.types import Districts

SECRETS = st.binary(min_size=32, max_size=32)
KEYS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789| -", min_size=1, max_size=40)
LAT = st.floats(40.49, 40.92)
LON = st.floats(-74.26, -73.69)


def _mac(secret):
    return lambda m: hmac.new(secret, m, hashlib.sha256).digest()


@settings(max_examples=300, deadline=None)
@given(SECRETS, KEYS, LAT, LON)
def test_offset_distance_in_range_and_deterministic(secret, key, lat, lon):
    off = PrivacyOffset(_mac(secret))
    moved = off.apply(key, lat, lon)
    assert 149.5 <= haversine_ft(lat, lon, *moved) <= 250.5
    assert PrivacyOffset(_mac(secret)).apply(key, lat, lon) == moved


@settings(max_examples=40, deadline=None)
@given(st.lists(st.integers(1, 60), min_size=1, max_size=12, unique=True), st.integers(1, 60))
def test_other_rows_never_change_a_row(houses, mine):
    ref = reference_of([(str(h), "Elm St", "11201", "Brooklyn", 40.6 + h * 0.0005, -73.95) for h in range(1, 61)])
    alone = place_rows([row("me", f"{mine} Elm St", "11201")], ref, None, NO_EXTRAS)
    others = [row(f"o{h}", f"{h} Elm St", "11201") for h in houses]
    mixed = place_rows(others + [row("me", f"{mine} Elm St", "11201")] + others, ref, None, NO_EXTRAS)
    assert mixed.results["me"] == alone.results["me"]
    assert mixed.building_keys["me"] == alone.building_keys["me"]


@settings(max_examples=300, deadline=None)
@given(st.floats(0, 10), st.floats(0, 10), st.floats(0.5, 4), st.floats(0.5, 4), st.floats(-1, 11), st.floats(-1, 11))
def test_point_in_polygon_with_a_hole(hx, hy, hw, hh, px, py):
    outer = [[-0.5, -0.5], [10.5, -0.5], [10.5, 10.5], [-0.5, 10.5], [-0.5, -0.5]]
    x1, y1 = min(hx + hw, 10), min(hy + hh, 10)
    hole = [[hx, hy], [x1, hy], [x1, y1], [hx, y1], [hx, hy]]
    if ring_contains(hole, px, py) == "boundary" or ring_contains(outer, px, py) == "boundary":
        return
    expected = bool(ring_contains(outer, px, py)) and not ring_contains(hole, px, py)
    assert polygon_contains([outer, hole], px, py) == expected


SPACING = st.sampled_from([" ", "  ", "   "])


@settings(max_examples=200, deadline=None)
@given(st.integers(1, 9999), st.integers(1, 199), st.sampled_from(["St", "Ave", "Pl", "Rd"]), SPACING,
       st.sampled_from(["", ".", ","]), st.booleans(), st.booleans())
def test_address_key_stable_and_sharp(house, n, typ, sp, punct, upper, ordinal):
    suffix = "th" if ordinal else ""
    a = f"W{punct}{sp}{n}{suffix}{sp}{typ}{punct}"
    a = a.upper() if upper else a
    k = address_key(str(house), a, "10011")
    assert k == address_key(str(house), f"West {n} {typ}", "10011")
    other_type = {"St": "Ave", "Ave": "Pl", "Pl": "Rd", "Rd": "St"}[typ]
    assert k != address_key(str(house), f"W {n} {other_type}", "10011")
    assert k != address_key(str(house), f"W {n + 1} {typ}", "10011")
    assert k != address_key(str(house + 1), f"W {n} {typ}", "10011")


@settings(max_examples=200, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 40), st.sampled_from("AB"), st.integers(1, 4)), max_size=120), st.integers(0, 15))
def test_small_cells_never_leave_1_to_max(entries, limit):
    rows = build_map_counts([MapEntry(f"u{u}", p, Districts(None, None, str(d))) for u, p, d in entries], limit)
    assert all(r.count is None or r.count > limit for r in rows)
