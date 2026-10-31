"""C-25: the old jitter drew from one stream for the whole run, so changing one row moved the rest. Each point depends only on
its own building and the secret (P-GEO-7)."""
from tests.support.geo import MAC, NO_EXTRAS, reference_of, row
from wholecount.engine.geo.offset import PrivacyOffset, haversine_ft
from wholecount.engine.geo.place import place_rows

PTS = [(str(i + 1), "Park Pl", z, "Brooklyn", 40.67 + i * 0.0003, -73.97) for i in range(33) for z in ("11217", "11238")]


def _moved(rows):
    pr = place_rows(rows, reference_of(PTS), None, NO_EXTRAS)
    off = PrivacyOffset(MAC)
    return pr, {k: off.apply(pr.building_keys[k], r.latitude, r.longitude) for k, r in pr.results.items()}


def test_changing_one_row_moves_no_other():
    rows = [row(f"r{i}", f"{i + 1} Park Pl", "11217") for i in range(33)]
    _, before = _moved(rows)
    changed = list(rows)
    changed[5] = row("r5", "6 Park Pl", "11238")
    _, after = _moved(changed)
    assert after["r5"] != before["r5"]
    assert {k: v for k, v in after.items() if k != "r5"} == {k: v for k, v in before.items() if k != "r5"}


def test_two_records_at_one_building_share_a_point():
    pr, moved = _moved([row("a", "3 Park Pl", "11217"), row("b", "3 Park Place", "11217")])
    assert moved["a"] == moved["b"]
    r = pr.results["a"]
    assert 149.5 <= haversine_ft(r.latitude, r.longitude, *moved["a"]) <= 250.5
