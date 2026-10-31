"""A-17: uninstalling closes Wholecount through Restart Manager and leaves an unrelated process running."""
import subprocess
import sys
import time

import pytest

from conftest import installer

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]


def test_uninstall_leaves_an_unrelated_process(tmp_path):
    setup = installer()
    target = tmp_path / "Wholecount"
    subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"], check=True, timeout=600)
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    app = subprocess.Popen([str(target / "Wholecount.exe")])
    try:
        time.sleep(5)
        subprocess.run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], check=True,
                       timeout=600)
        time.sleep(3)
        assert app.poll() is not None
        assert other.poll() is None
    finally:
        other.terminate()
        if app.poll() is None:
            app.terminate()
