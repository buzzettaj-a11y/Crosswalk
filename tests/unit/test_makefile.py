"""The Makefile gives the same target names as CLAUDE.md, and its stubs never look green."""
import re
import shutil
import subprocess

import pytest

from tests.conftest import ROOT

TARGETS = ("test", "offline", "copy", "screens", "run", "bundle", "lock")

needs_make = pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")


def test_targets_exist():
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    defined = set(re.findall(r"^([a-z]+):", text, re.M))
    assert set(TARGETS) <= defined


@needs_make
@pytest.mark.parametrize("target,milestone", [("bundle", "M14")])
def test_stubs_exit_1_and_name_their_milestone(target, milestone):
    p = subprocess.run(["make", "-s", target], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode != 0
    assert f"arrives in {milestone}" in p.stdout


@needs_make
def test_targets_run_the_documented_commands():
    p = subprocess.run(["make", "-n", "test", "offline", "copy", "run"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    lines = [ln.strip() for ln in p.stdout.splitlines()]
    assert "python -m pytest -q" in lines
    assert "python -m pytest -q tests/offline" in lines
    assert "python -m pytest -q tests/copy" in lines
    assert "python -m wholecount" in lines


@needs_make
def test_screens_target_runs_the_tool_offscreen():
    p = subprocess.run(["make", "-n", "screens"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0 and "python -m tools.screens" in p.stdout
    assert "screens: export QT_QPA_PLATFORM = offscreen" in (ROOT / "Makefile").read_text(encoding="utf-8")


def test_test_target_exports_offscreen_qt():
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^test: export QT_QPA_PLATFORM = offscreen$", text, re.M)
