"""A silent install adds exactly two Block rules on the installed exe, a second install keeps two, and uninstall removes both
and the folder (M14). Settles whether netsh's name= is PowerShell's DisplayName (Unconfirmed in the research)."""
import subprocess
import sys

import pytest

from conftest import installer
from _ps import ps_json

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]


def install(setup, target, log):
    subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={log}", f"/DIR={target}"],
                   check=True, timeout=600)


def rules():
    return ps_json("Get-NetFirewallRule -DisplayName 'Wholecount offline*' | Select-Object DisplayName, Direction, Action, "
                   "Enabled, @{n='Profile';e={$_.Profile.ToString()}}, @{n='Program';e={($_ | "
                   "Get-NetFirewallApplicationFilter).Program}}")


def test_install_twice_then_uninstall(tmp_path):
    setup = installer()
    target = tmp_path / "Wholecount"
    install(setup, target, tmp_path / "install.log")
    got = rules()
    assert sorted(r["DisplayName"] for r in got) == ["Wholecount offline (in)", "Wholecount offline (out)"]
    for r in got:
        assert str(r["Action"]) in ("Block", "4") and str(r["Enabled"]) in ("True", "1")
        assert r["Profile"] == "Any" and r["Program"].lower() == str(target / "Wholecount.exe").lower()
    install(setup, target, tmp_path / "install2.log")
    assert len(rules()) == 2
    subprocess.run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], check=True, timeout=600)
    assert rules() == [] and not (target / "Wholecount.exe").exists()
