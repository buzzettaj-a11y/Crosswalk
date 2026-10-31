"""Real Geosupport on Joe's Windows machine (M05 Windows checks). Skipped unless Geosupport is installed."""
import csv
import os
import pathlib
import sys

import pytest

from wholecount.engine.geo.geosupport import GeosupportBackend, release_quarter

HERE = pathlib.Path(__file__).resolve().parent
BACKEND, REASON = GeosupportBackend.discover(os.environ) if sys.platform == "win32" else (None, "not_windows")

pytestmark = pytest.mark.skipif(BACKEND is None, reason=f"Geosupport not found ({REASON})")


def test_landmarks_place_high_with_districts():
    rows = list(csv.DictReader((HERE / "landmarks.csv").open(encoding="utf-8")))
    assert len(rows) == 12
    for r in rows:
        res = BACKEND.lookup(r["house"], r["street"], r["zip"])
        assert res.confidence == "high", r["landmark"]
        assert res.districts is not None and res.districts.any(), r["landmark"]


def test_release_is_read():
    assert BACKEND.release == "unknown" or release_quarter(BACKEND.release) is not None
