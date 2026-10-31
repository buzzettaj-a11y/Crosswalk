"""Every PowerShell script parses (M14). Runs none of them."""
import pathlib
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "tools").rglob("*.ps1"))


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_parses(script):
    cmd = ("$e = $null; [System.Management.Automation.Language.Parser]::ParseFile("
           f"'{script}', [ref]$null, [ref]$e) | Out-Null; if ($e.Count) {{ $e | ForEach-Object {{ $_.Message }}; exit 1 }}")
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
