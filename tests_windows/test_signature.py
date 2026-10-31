"""Both files are signed with the CI certificate and read Valid once it is trusted (M14). The installer holds the signed exe."""
import os
import subprocess
import sys

import pytest

from conftest import dist, installer
from _ps import ps_json

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]


def sig(path):
    return ps_json(f"Get-AuthenticodeSignature '{path}' | Select-Object @{{n='Status';e={{$_.Status.ToString()}}}}, "
                   "@{n='Thumb';e={$_.SignerCertificate.Thumbprint}}")[0]


def test_both_files_are_signed_by_the_same_certificate(tmp_path):
    exe, setup = sig(dist() / "Wholecount.exe"), sig(installer())
    assert exe["Status"] == "Valid" and setup["Status"] == "Valid"
    assert exe["Thumb"] == setup["Thumb"]
    want = os.environ.get("WHOLECOUNT_CI_THUMBPRINT")
    if want:
        assert exe["Thumb"] == want
    target = tmp_path / "Wholecount"
    subprocess.run([str(installer()), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"], check=True,
                   timeout=600)
    try:
        assert sig(target / "Wholecount.exe")["Thumb"] == exe["Thumb"]
    finally:
        subprocess.run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=600)
