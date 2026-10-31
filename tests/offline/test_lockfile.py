"""Layer: supply chain (H1, H2, SPEC 12.1 layer 5, research section 8). The approved set is the real control.

R6's two lock tests run on requirements.lock. The rest cover the dev lock, the .in files and pyproject.toml.
Every check has a negative control that feeds the same helper a bad lock.
"""
import tomllib

import pytest

from tests.conftest import DEV_LOCK, LOCK, ROOT
from tools.offline_rules import APPROVED_DEV_DISTS, APPROVED_DISTS, FORBIDDEN_DISTS
from tools.offline_scan import check_lock_approved, check_lock_clean, in_file_names, lock_pins

pytestmark = pytest.mark.claim("CL-OFFLINE-01")

HASH = " \\\n    --hash=sha256:" + "0" * 64 + "\n"


# R6

def test_lockfile_is_hashed_pinned_and_clean():
    assert check_lock_clean(LOCK.read_text(encoding="utf-8")) == []


def test_lockfile_pins_exactly_the_approved_distributions():
    assert check_lock_approved(LOCK.read_text(encoding="utf-8"), APPROVED_DISTS) == ([], [])


def test_runtime_lock_has_the_eleven_research_distributions():
    assert len(APPROVED_DISTS) == 11
    assert set(lock_pins(LOCK.read_text(encoding="utf-8"))) == APPROVED_DISTS


# Added in M00

def test_dev_lock_is_hashed_and_clean():
    assert check_lock_clean(DEV_LOCK.read_text(encoding="utf-8")) == []


def test_dev_lock_pins_are_approved_or_approved_dev():
    assert check_lock_approved(DEV_LOCK.read_text(encoding="utf-8"), APPROVED_DISTS | APPROVED_DEV_DISTS) == ([], [])


def test_approved_dev_dists_are_not_runtime_and_not_forbidden():
    assert not APPROVED_DEV_DISTS & APPROVED_DISTS
    assert not (APPROVED_DEV_DISTS | APPROVED_DISTS) & FORBIDDEN_DISTS


def test_dev_lock_has_every_runtime_pin_at_the_same_version():
    runtime, dev = lock_pins(LOCK.read_text(encoding="utf-8")), lock_pins(DEV_LOCK.read_text(encoding="utf-8"))
    assert {n: dev.get(n) for n in runtime} == runtime


def test_in_files_name_only_approved_distributions():
    runtime = in_file_names((ROOT / "requirements.in").read_text(encoding="utf-8"))
    dev = in_file_names((ROOT / "requirements-dev.in").read_text(encoding="utf-8"))
    assert set(runtime) <= APPROVED_DISTS, runtime
    assert set(dev) <= APPROVED_DISTS | APPROVED_DEV_DISTS, dev
    assert "pyside6" not in runtime + dev
    assert "pyside6-essentials" in runtime


def test_pyproject_lists_no_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == []
    assert "optional-dependencies" not in project
    assert project["requires-python"] == ">=3.12,<3.13"


def test_negative_controls():
    good = "numpy==2.0.0" + HASH
    assert check_lock_clean(good) == []
    assert check_lock_clean("numpy==2.0.0\n") == ["no hash: numpy"]
    assert check_lock_clean("") == ["empty lockfile"]
    assert any("forbidden" in x for x in check_lock_clean(good + "requests==2.0.0" + HASH))
    assert any("forbidden" in x for x in check_lock_clean(good + "streamlit==1.0.0" + HASH))
    assert any("pinned" in x for x in check_lock_clean(good + "-e git+https://example.com/x.git\n"))
    assert any("range" in x for x in check_lock_clean(good + "six>=1.0" + HASH))
    assert check_lock_approved(good + "extra-pkg==1.0" + HASH, {"numpy"}) == (["extra-pkg"], [])
    assert check_lock_approved(good, {"numpy", "pandas"}) == ([], ["pandas"])
    assert in_file_names("-c requirements.lock\n# comment\nPySide6_Essentials>=6 # ui\nlxml>=6.1.3\n") == ["pyside6-essentials", "lxml"]


def test_negative_control_for_the_version_match(tmp_path):
    runtime = lock_pins("numpy==2.0.0" + HASH)
    dev = lock_pins("numpy==2.0.1" + HASH + "pytest==8.0.0" + HASH)
    assert {n: dev.get(n) for n in runtime} != runtime
