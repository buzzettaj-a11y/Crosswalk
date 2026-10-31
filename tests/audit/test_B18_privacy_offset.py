"""B-18: the old jitter used random.Random(1337) in row order, so it could be undone and averaged away. The offset is now an HMAC
of the install secret and the building's address key (P-GEO-7)."""
import random
import statistics

from tests.conftest import ROOT
from tests.support.geo import MAC, OTHER_MAC
from wholecount import copy
from wholecount.engine.geo.mapdata import MapPointEntry, build_map_points
from wholecount.engine.geo.offset import PrivacyOffset, haversine_ft, move_point, stable_offset

GOLDEN = [("100|west 10 street|10011", 40.7350, -73.9990, 172.6566, 0.400361, 40.7354354, -73.9987568),
          ("1|main street|11201", 40.7000, -73.9900, 219.2855, 2.221391, 40.6996364, -73.9893698),
          ("11|main street|11201", 40.7040, -73.9800, 197.7307, 5.418447, 40.7043513, -73.9805434)]
KEYS = [(f"{n}|street {n % 37}|1{n % 90:04d}", 40.6 + (n % 50) * 0.004, -74.0 + (n % 40) * 0.005) for n in range(400)]


def test_a_golden_vectors():
    for key, lat, lon, ft, bearing, mlat, mlon in GOLDEN:
        d, b = stable_offset(MAC, key)
        assert (round(d, 4), round(b, 6)) == (ft, bearing)
        assert tuple(round(v, 7) for v in move_point(lat, lon, d, b)) == (mlat, mlon)
    d, b = stable_offset(OTHER_MAC, GOLDEN[0][0])
    assert (round(d, 4), round(b, 6)) == (182.2046, 2.198796)
    assert tuple(round(v, 7) for v in move_point(40.7350, -73.9990, d, b)) == (40.7347069, -73.9984672)


def test_b_distances_in_range_stable_and_order_free():
    off = PrivacyOffset(MAC)
    first = {k: off.apply(k, lat, lon) for k, lat, lon in KEYS}
    for k, lat, lon in KEYS:
        assert 149.5 <= haversine_ft(lat, lon, *first[k]) <= 250.5
    assert {k: off.apply(k, lat, lon) for k, lat, lon in KEYS} == first
    shuffled = list(KEYS)
    random.Random(7).shuffle(shuffled)
    assert {k: off.apply(k, lat, lon) for k, lat, lon in shuffled} == first


def test_c_subtracting_the_old_jitter_leaves_a_large_error():
    off = PrivacyOffset(MAC)
    old = random.Random(1337)
    errors = []
    for k, lat, lon in KEYS:
        mlat, mlon = off.apply(k, lat, lon)
        guess_ft, guess_b = 150 + 100 * old.random(), 2 * 3.141592653589793 * old.random()
        glat, glon = move_point(lat, lon, guess_ft, guess_b)
        errors.append(haversine_ft(lat, lon, mlat - (glat - lat), mlon - (glon - lon)))
    assert statistics.median(errors) > 100


def test_d_no_seed_or_1337_in_settings_copy_or_audit_text():
    texts = [p.read_text(encoding="utf-8") for p in (ROOT / "wholecount" / "settings").glob("*.toml")]
    texts += [e.text for e in copy.all_entries()]
    texts += [e.text for e in copy.all_entries() if e.key.startswith("audit.")]
    for t in texts:
        assert "1337" not in t and "seed" not in t.lower()


def test_e_three_hundred_clients_at_one_door():
    key, lat, lon = "100|west 10 street|10011", 40.7350, -73.9990
    entries = [MapPointEntry("P", key, lat, lon) for _ in range(300)]
    runs = [build_map_points(entries, MAC) for _ in range(4)]
    pts = {(p.latitude, p.longitude) for p in runs[0]}
    assert len(pts) == 1
    (mlat, mlon), = pts
    assert 149.5 <= haversine_ft(lat, lon, mlat, mlon) <= 250.5
    assert all(r == runs[0] for r in runs)
    assert build_map_points(list(reversed(entries)), MAC) == runs[0]
    assert {(p.latitude, p.longitude) for p in build_map_points(entries, OTHER_MAC)} != pts
    centroid = (statistics.fmean(p.latitude for p in runs[0]), statistics.fmean(p.longitude for p in runs[0]))
    assert haversine_ft(*centroid, mlat, mlon) < 0.01
    assert haversine_ft(*centroid, lat, lon) > 149
