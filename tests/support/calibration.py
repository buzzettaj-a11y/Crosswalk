"""Helpers for M13 calibration tests: a processed session over the population fixture, with a fake DPAPI."""
import shutil

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from tests.support.fake_dpapi import FakeDpapi
from wholecount.session.calibration import CalibrationSession
from wholecount.session.runner import process

FIX = ROOT / "tests" / "fixtures" / "calibration"


def population_session(tmp_path, names=("people_a.csv", "people_b.csv"), **kw):
    (tmp_path / "in").mkdir(parents=True, exist_ok=True)
    paths = [shutil.copy(FIX / n, tmp_path / "in" / n) for n in names]
    s = r_fixture.session(tmp_path / "w", paths=paths, **kw)
    s.calibration_dir = tmp_path / "calibration"
    process(s)
    return s


def draw(s, per_band=5, dp=None):
    dp = dp or FakeDpapi()
    return CalibrationSession.draw(s, per_band, dp.protect, dp.unprotect), dp


def label_all(cal, who, rule):
    """rule(pair) -> same, different or unsure."""
    for p in cal.pairs:
        cal.label(who, p.pair_id, rule(p))
    cal.finish(who)
