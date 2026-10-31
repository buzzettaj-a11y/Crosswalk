"""The installer's Geosupport check agrees with M05's discover() (M14). Skipped unless Geosupport is installed."""
import os
import subprocess
import sys

import pytest

from conftest import installer

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]


def test_installer_log_matches_discover(tmp_path):
    from wholecount.guard.config import discover_geosupport_dirs

    dirs = discover_geosupport_dirs(os.environ, os.path.isdir)
    if not dirs:
        pytest.skip("Geosupport Desktop Edition is not installed")
    log = tmp_path / "install.log"
    target = tmp_path / "Wholecount"
    subprocess.run([str(installer()), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={log}", f"/DIR={target}"],
                   check=True, timeout=600)
    try:
        assert "Geosupport check: found" in log.read_text(encoding="utf-8", errors="replace")
    finally:
        subprocess.run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=600)
