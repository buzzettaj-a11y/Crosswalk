"""The M08 R and S fixture for M09, with Fay Gil written Fay Gíl and Client_ID 00123 on R01. Counts don't change."""
import json

from tests.fixtures.session import r_fixture
from tests.support.session import decide_all
from wholecount.engine.geo.districts import DistrictIndex
from wholecount.session import commands as C
from wholecount.session.runner import process


def rows():
    rs = r_fixture.r_rows()
    rs[0][0] = "00123"
    rs[5][2] = "Gíl"
    return rs


def districts(tmp_path):
    square = [[-74.0, 40.68], [-73.97, 40.68], [-73.97, 40.71], [-74.0, 40.71], [-74.0, 40.68]]
    p = tmp_path / "districts.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "senate_district": 26, "assembly_district": 52, "council_district": 33}, "geometry": {"type": "Polygon", "coordinates": [square]}}]}))
    return DistrictIndex.from_files([p])


def session(tmp_path, state="base", ack=True, **kw):
    src = tmp_path / "in"
    s = r_fixture.session(src, paths=r_fixture.files(src, r=rows()), districts=districts(tmp_path), **kw)
    process(s)
    if state == "decided":
        decide_all(s)
    if ack and s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    return s


VALUES = sorted({v for row in rows() + r_fixture.s_rows() for v in row[1:8] if len(v) > 2}
                - {"Brooklyn", "Housing", "Youth", "Workforce", "Total"})
