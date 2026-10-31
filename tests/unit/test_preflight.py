"""preflight (P-GEO-4, fix plan 5.3): the backend a batch of the operator's own files would use."""
import datetime as dt
import shutil

import pytest

from tests.support.geo import FIX, SAMPLE
from wholecount import copy
from wholecount.engine.geo.backend import preflight, release_stale
from wholecount.engine.geo.geosupport import GeosupportBackend

NONE = lambda environ: (None, "not_installed")  # noqa: E731
TODAY = dt.date(2026, 10, 30)


def _pf(tmp_path, discover=NONE, today=TODAY):
    return preflight({}, tmp_path, today, discover=discover, district_dir=tmp_path / "no_districts")


@pytest.mark.claim("CL-GEO-PRE-01")
def test_sample_copied_into_the_folder_is_sample_and_not_placed(tmp_path):
    (tmp_path / "reference").mkdir()
    shutil.copy(SAMPLE, tmp_path / "reference" / "my_points.csv")
    pf = _pf(tmp_path)
    assert (pf.reference_kind, pf.backend_name, pf.can_place) == ("sample", "none", False)
    assert "practice sample" in copy.get("geo.preflight.sample_refused")


def test_sample_found_by_hash_without_its_first_line(tmp_path):
    (tmp_path / "reference").mkdir()
    body = SAMPLE.read_bytes()
    (tmp_path / "reference" / "a.csv").write_bytes(body)
    assert _pf(tmp_path).reference_kind == "sample"
    stripped = b"\n".join(body.split(b"\n")[1:])
    (tmp_path / "reference" / "a.csv").write_bytes(stripped)
    assert _pf(tmp_path).reference_kind == "real"


@pytest.mark.claim("CL-GEO-PRE-02")
def test_two_files_give_several_reference_files(tmp_path):
    (tmp_path / "reference").mkdir()
    shutil.copy(FIX / "refdata_b17.csv", tmp_path / "reference" / "a.csv")
    shutil.copy(FIX / "refdata_b17.csv", tmp_path / "reference" / "b.csv")
    pf = _pf(tmp_path)
    assert (pf.reference_kind, pf.can_place) == ("several_reference_files", False)
    assert "more than one file" in copy.get("geo.preflight.several_reference_files")


def test_real_reference_can_place(tmp_path):
    (tmp_path / "reference").mkdir()
    shutil.copy(FIX / "refdata_b17.csv", tmp_path / "reference" / "a.csv")
    pf = _pf(tmp_path)
    assert (pf.reference_kind, pf.backend_name, pf.reference_rows, pf.can_place) == ("real", "reference", 18, True)


@pytest.mark.claim("CL-GEO-PRE-03")
def test_missing_folder_gives_none(tmp_path):
    pf = _pf(tmp_path)
    assert (pf.reference_kind, pf.backend_name, pf.can_place, pf.district_files) == ("none", "none", False, 0)
    assert "no geocoder" in copy.get("geo.preflight.no_geocoder")


@pytest.mark.claim("CL-GEO-PRE-04")
def test_release_stale_by_quarter():
    assert release_stale("25C", dt.date(2026, 10, 1))
    assert not release_stale("25C", dt.date(2026, 9, 30))
    assert not release_stale("unknown", dt.date(2040, 1, 1))
    assert "more than a year old" in copy.get("geo.preflight.release_stale", release="25C")


def test_geosupport_preflight_reports_release(tmp_path):
    geo = GeosupportBackend(object(), KeyError, "25C")
    pf = _pf(tmp_path, discover=lambda environ: (geo, "ok"), today=dt.date(2027, 1, 1))
    assert (pf.backend_name, pf.release, pf.release_stale, pf.can_place) == ("geosupport", "25C", True, True)


@pytest.mark.claim("CL-GEO-PRE-05")
def test_district_files_counted(tmp_path):
    d = tmp_path / "districts"
    d.mkdir()
    shutil.copy(FIX / "districts_donut.geojson", d / "a.geojson")
    (d / "README.txt").write_text("not a district file")
    assert preflight({}, tmp_path, TODAY, discover=NONE, district_dir=d).district_files == 1
    assert "no districts" in copy.get("geo.preflight.no_district_files")


def test_shipped_district_folder_has_a_readme_and_no_files_yet():
    pf = preflight({}, "/nonexistent", TODAY, discover=NONE)
    from wholecount.engine.geo.backend import district_paths
    assert pf.district_files == len(district_paths())
