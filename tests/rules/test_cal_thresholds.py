"""Saving the proposal and Likely lines (M13 CAL-7)."""
import json

import pytest

from tests.support.session import base
from wholecount.session.calibration import CalibrationRefused, SetThresholds, thresholds
from wholecount.session.store import Store


@pytest.mark.parametrize("pair", [(39, 90), (62, 62), (80, 70), (62, 201), (62.0, 90)])
def test_bad_ranges_are_refused(pair):
    with pytest.raises(CalibrationRefused):
        SetThresholds(*pair)


def test_saved_audited_and_identity_goes_stale(tmp_path):
    s = base(tmp_path / "w")
    store = Store(tmp_path / "data", protect=lambda b: b, unprotect=lambda b: b)
    SetThresholds(70, 95).run(s, store)
    assert thresholds(s) == (70, 95)
    prefs = json.loads((tmp_path / "data" / "prefs.json").read_text())
    assert prefs["thresholds"]["possible_min"] == 70 and prefs["thresholds"]["reviewer"] == "Joe"
    lines = [e for e in s.audit if e.code == "THRESHOLD_SET"]
    assert [(e.get("field_name"), e.get("count")) for e in lines] == [(["possible_min"], [70]), (["likely_min"], [95])]
    assert all(e.get("reviewer") == ["Joe"] for e in lines)
    assert "identity" in s.stale and "sources" not in s.stale
    from wholecount.session.runner import process
    process(s)
    assert all(p.score >= 70 for p in s.results.identity.proposals)
