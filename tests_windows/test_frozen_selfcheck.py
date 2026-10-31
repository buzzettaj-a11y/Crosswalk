"""The built exe and the installed exe pass every self-check, with the same counts as the Linux source run (M14)."""
import json
import subprocess
import sys

import pytest

from conftest import ROOT, dist, installer

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]


def check(exe, out):
    subprocess.run([str(exe), "--self-check", "--self-check-out", str(out)], check=True, timeout=600)
    data = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert all(v == "ok" for v in data["checks"].values()), data["checks"]
    assert data["frozen"] is True
    return data["counts"]


def expected():
    after = json.loads((ROOT / "wholecount" / "sample_data" / "EXPECTED.json").read_text(encoding="utf-8"))["counts"][
        "after_decisions"]
    return {"counted": after["counted"], "not_counted_yet": after["not_counted_yet"], "set_aside": after["set_aside"],
            "goal_1": after["goal_1"]["high"], "goal_2": after["goal_2"]["high"]}


def test_built_exe(tmp_path):
    counts = check(dist() / "Wholecount.exe", tmp_path / "built")
    assert {k: counts[k] for k in expected()} == expected()


def test_installed_exe(tmp_path):
    target = tmp_path / "Wholecount"
    subprocess.run([str(installer()), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"], check=True,
                   timeout=600)
    try:
        counts = check(target / "Wholecount.exe", tmp_path / "installed")
        assert {k: counts[k] for k in expected()} == expected()
    finally:
        subprocess.run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=600)
