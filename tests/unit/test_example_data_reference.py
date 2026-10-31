"""The practice reference (P-GEO-4, P-GEO-4a): it loads, is a sample, and places every example address EXPECTED.json says it
places, with the planned location split per file. A run with no backend reads no geocoder."""
import collections
import hashlib
import subprocess
import sys

import pytest

from tests.conftest import ROOT
from tests.support.example import PLAN, standardized_example
from tests.support.geo import NO_EXTRAS, SAMPLE
from wholecount.engine.geo.backend import NoBackend, select_backend
from wholecount.engine.geo.place import outcome_for, place_rows
from wholecount.engine.geo.reference import SAMPLE_MARKER, SAMPLE_REFERENCE_HASHES, ReferenceBackend
from wholecount.engine.standardize.model import location_for

LOC = PLAN["locations"]


@pytest.fixture(scope="module")
def std():
    return standardized_example()


def _split(rows, pr):
    out = {"mapped_high": 0, "mapped_low": 0, "not_mapped": collections.Counter()}
    for r in rows:
        if not r.count_status.counted:
            continue
        o = outcome_for(location_for(r), pr.results.get(r.record_key))
        if o.kind == "mapped":
            out[f"mapped_{o.confidence}"] += 1
        else:
            out["not_mapped"][o.reason] += 1
    return out


def test_sample_loads_and_is_marked():
    ref = ReferenceBackend.from_path(SAMPLE)
    assert ref.is_sample and ref.rows == LOC["reference_rows"]
    assert SAMPLE.read_text(encoding="utf-8").splitlines()[0] == SAMPLE_MARKER
    assert hashlib.sha256(SAMPLE.read_bytes()).hexdigest() in SAMPLE_REFERENCE_HASHES


@pytest.mark.parametrize("run", ["practice_run", "no_backend_run"])
def test_location_split_matches_the_plan(std, run):
    backend = select_backend(None, ReferenceBackend.from_path(SAMPLE), allow_sample=True) if run == "practice_run" else NoBackend()
    looked_up = 0
    for name, rows in std.items():
        pr = place_rows(rows, backend, None, NO_EXTRAS)
        looked_up += len(pr.results)
        got, want = _split(rows, pr), LOC[run][name]
        assert (got["mapped_high"], got["mapped_low"]) == (want["mapped_high"], want["mapped_low"]), name
        assert {k: v for k, v in got["not_mapped"].items() if v} == {k: v for k, v in want["not_mapped"].items() if v}, name
        assert pr.practice == (run == "practice_run")
    assert looked_up == LOC["looked_up"]


def test_planned_not_found_rows(std):
    backend = select_backend(None, ReferenceBackend.from_path(SAMPLE), allow_sample=True)
    found = []
    for name, rows in std.items():
        pr = place_rows(rows, backend, None, NO_EXTRAS)
        found += [[name, r.row_number] for r in rows if r.record_key in pr.results and not pr.results[r.record_key].placed]
    assert sorted(found) == LOC["planned_not_found_rows"]


def test_generator_check_still_passes():
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "make_example_data.py"), "--check"], capture_output=True, text=True,
                       timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
