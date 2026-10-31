"""The build lock (M14 section 1, SPEC 12.1 layer 5): hashed, pinned, clean, and exactly the approved set. Every pip install
in the workflows, scripts and Makefile carries --require-hashes, --no-deps and --only-binary=:all:."""
import re

import pytest

from tests.conftest import DEV_LOCK, ROOT
from tools.offline_rules import APPROVED_BUILD_DISTS, APPROVED_DEV_DISTS, APPROVED_DISTS, FORBIDDEN_DISTS
from tools.offline_scan import check_lock_approved, check_lock_clean, in_file_names, lock_pins

BUILD_LOCK = ROOT / "requirements-build.lock"
FLAGS = ("--require-hashes", "--no-deps", "--only-binary=:all:")


def test_build_lock_is_hashed_pinned_and_clean():
    assert check_lock_clean(BUILD_LOCK.read_text(encoding="utf-8")) == []


def test_build_lock_pins_exactly_the_approved_sets():
    text = BUILD_LOCK.read_text(encoding="utf-8")
    pins = set(lock_pins(text))
    assert pins <= APPROVED_DISTS | APPROVED_DEV_DISTS | APPROVED_BUILD_DISTS
    assert APPROVED_BUILD_DISTS <= pins
    assert "pyinstaller" in pins


def test_build_dists_are_new_and_not_forbidden():
    assert not APPROVED_BUILD_DISTS & (APPROVED_DISTS | APPROVED_DEV_DISTS)
    assert not APPROVED_BUILD_DISTS & FORBIDDEN_DISTS


def test_shared_pins_match_the_dev_lock():
    build, dev = lock_pins(BUILD_LOCK.read_text(encoding="utf-8")), lock_pins(DEV_LOCK.read_text(encoding="utf-8"))
    assert {n: v for n, v in build.items() if n in dev} == {n: dev[n] for n in build if n in dev}


def test_build_in_names_only_approved_dists():
    names = in_file_names((ROOT / "requirements-build.in").read_text(encoding="utf-8"))
    assert set(names) <= APPROVED_DEV_DISTS | APPROVED_BUILD_DISTS, names


def pip_install_problems(text):
    """Each pip install line (with its continuations) lacking one of the three flags, or carrying --no-require-hashes."""
    out = []
    joined = re.sub(r"[\\`]\s*\n\s*", " ", text)
    for line in joined.splitlines():
        if line.strip().startswith("#"):        # a comment runs nothing (the Makefile explains the pip-tools venv)
            continue
        if re.search(r"\bpip(?:3)?\s+install\b", line):
            missing = [f for f in FLAGS if f not in line]
            if missing or "--no-require-hashes" in line:
                out.append(line.strip())
    return out


def scanned_files():
    files = list((ROOT / ".github" / "workflows").glob("*.yml")) + list((ROOT / "tools").rglob("*.ps1")) + [ROOT / "Makefile"]
    return [f for f in files if f.exists()]


def test_every_pip_install_has_the_three_flags():
    bad = {f.name: pip_install_problems(f.read_text(encoding="utf-8")) for f in scanned_files()}
    assert {k: v for k, v in bad.items() if v} == {}


def test_negative_controls():
    assert pip_install_problems("pip install -r x.lock\n")
    assert not pip_install_problems("# pip install pip-tools in a throwaway venv\n")
    assert pip_install_problems("python -m pip install --require-hashes --no-deps -r x.lock\n")
    assert pip_install_problems("pip install --require-hashes --no-deps --only-binary=:all: --no-require-hashes -r x\n")
    assert not pip_install_problems("python -m pip install --require-hashes --no-deps `\n  --only-binary=:all: -r x.lock\n")
    good = "pyinstaller==6.0" + " \\\n    --hash=sha256:" + "0" * 64 + "\n"
    assert check_lock_approved(good + "requests==2.0" + " \\\n    --hash=sha256:" + "0" * 64 + "\n",
                               APPROVED_BUILD_DISTS)[0] == ["requests"]


@pytest.mark.parametrize("dist", sorted(APPROVED_BUILD_DISTS))
def test_each_build_dist_is_pinned(dist):
    assert dist in lock_pins(BUILD_LOCK.read_text(encoding="utf-8"))
