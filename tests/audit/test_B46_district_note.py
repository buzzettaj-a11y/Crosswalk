"""B-46: a moved point can land across a district line. Districts come from the true point, and a note says so (P-GEO-7)."""
import hashlib
import hmac
import json

import pytest

from tests.support.geo import NO_EXTRAS, reference_of, row
from wholecount import copy
from wholecount.engine.geo.districts import DistrictIndex
from wholecount.engine.geo.offset import PrivacyOffset
from wholecount.engine.geo.place import place_rows

# Two squares meeting at longitude -73.95. A point 5 ft west of the line is inside district A (council 7).
FT_IN_DEG_LON = 1 / (111_320 / 0.3048 * 0.7570)
LAT, LON = 40.70, -73.95 - 5 * FT_IN_DEG_LON


def _index(tmp_path):
    def sq(n, x0, x1):
        return {"type": "Feature", "properties": {"council_district": n},
                "geometry": {"type": "Polygon", "coordinates": [[[x0, 40.6], [x1, 40.6], [x1, 40.8], [x0, 40.8], [x0, 40.6]]]}}
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [sq(7, -74.05, -73.95), sq(8, -73.95, -73.85)]}))
    return DistrictIndex.from_files([p])


def test_district_from_the_true_point_and_moved_point_can_cross(tmp_path):
    idx = _index(tmp_path)
    ref = reference_of([("5", "Line St", "11201", "Brooklyn", LAT, LON)])
    crossed = 0
    for n in range(40):
        secret = bytes((n + i) % 256 for i in range(32))
        mac = lambda m, s=secret: hmac.new(s, m, hashlib.sha256).digest()
        pr = place_rows([row("r", "5 Line St", "11201")], ref, idx, NO_EXTRAS)
        res = pr.results["r"]
        assert res.districts.council == "7"
        moved = PrivacyOffset(mac).apply(pr.building_keys["r"], res.latitude, res.longitude)
        crossed += idx.assign(*moved).council == "8"
    assert crossed >= 1


@pytest.mark.claim("CL-GEO-OFFSET-01")
def test_moved_point_note_exists():
    text = copy.get("geo.moved_point_note")
    assert "150 to 250 feet" in text and "district line" in text and "true location" in text
    s = PrivacyOffset(lambda m: b"\x00" * 32)
    assert (s.min_ft, s.max_ft) == (150.0, 250.0)
