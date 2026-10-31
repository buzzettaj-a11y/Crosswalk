"""The netsh and PowerShell lines in docs/IT_TRUST.md equal the installer's, so the doc can't drift (M14 section 6)."""
import re

from tests.conftest import ROOT
from tests.unit.test_iss import netsh_params

DOC = (ROOT / "docs" / "IT_TRUST.md").read_text(encoding="utf-8")
APP = r"C:\Program Files\Wholecount"


def test_every_installer_netsh_line_is_in_the_doc():
    for params in netsh_params("Run"):
        assert "netsh " + params.replace("{app}", APP) in DOC, params


def test_the_powershell_lines_match_the_rules():
    rules = re.findall(r'name="(Wholecount offline \((?:out|in)\))" dir=(out|in)', "\n".join(netsh_params("Run")))
    for name, d in rules:
        direction = "Outbound" if d == "out" else "Inbound"
        assert (f"New-NetFirewallRule -DisplayName '{name}' -Direction {direction} -Action Block "
                f"-Program '{APP}\\Wholecount.exe' -Profile Any -Enabled True") in DOC
        assert f"Remove-NetFirewallRule -DisplayName '{name}'" in DOC


def test_negative_control():
    assert "netsh advfirewall firewall add rule name=\"Wholecount offline (out)\" dir=out action=allow" not in DOC
