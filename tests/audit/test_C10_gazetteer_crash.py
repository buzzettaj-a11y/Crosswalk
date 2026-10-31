"""C-10: two district loaders returned different shapes and the run crashed. One loader now, and each source runs end to end
(P-GEO-8)."""
import pytest

from tests.support.geo import NO_EXTRAS, SAMPLE, donut, fake, ref_b17, row
from wholecount.engine.geo.backend import select_backend
from wholecount.engine.geo.districts import DistrictIndex
from wholecount.engine.geo.place import place_rows
from wholecount.engine.geo.reference import ReferenceBackend

SAMPLE_ROW = SAMPLE.read_text(encoding="utf-8").splitlines()[2].split(",")


@pytest.mark.parametrize("source", ["fake", "reference_with_districts", "sample", "reference_no_districts"])
def test_each_source_places_with_no_crash(source):
    rows = [row("r1", "1 Main St", "11201")]
    if source == "fake":
        backend, districts = fake(), donut()
    elif source == "reference_with_districts":
        backend, districts = select_backend(None, ref_b17()), donut()
    elif source == "sample":
        backend = select_backend(None, ReferenceBackend.from_path(SAMPLE), allow_sample=True)
        districts = DistrictIndex.from_files([])
        house, street, zip5, city = SAMPLE_ROW[:4]
        rows = [row("r1", f"{house} {street}", zip5, city=city)]
    else:
        backend, districts = select_backend(None, ref_b17()), DistrictIndex.from_files([])
    assert isinstance(districts, DistrictIndex)
    pr = place_rows(rows, backend, districts, NO_EXTRAS)
    r = pr.results["r1"]
    assert r.placed and r.latitude is not None and r.longitude is not None
    if source in ("fake", "reference_with_districts"):
        assert r.districts is not None and r.districts.any()
    if source == "reference_no_districts":
        assert r.districts is None
    assert pr.practice == (source == "sample")
