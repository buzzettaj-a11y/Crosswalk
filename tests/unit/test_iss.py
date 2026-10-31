"""installer/wholecount.iss (M14 section 4): the directives, the four netsh lines and two uninstall lines, the launch entry,
no network use, the wording rules, and the same Geosupport paths as M05."""
import json
import re

from tests.conftest import ROOT
from wholecount.guard.config import GEOSUPPORT_DEFAULT_DIRS

ISS = (ROOT / "installer" / "wholecount.iss").read_text(encoding="utf-8")
EM_DASH = "\u2014"


def section(name):
    m = re.search(r"^\[" + re.escape(name) + r"\]\n(.*?)(?=^\[|\Z)", ISS, re.M | re.S)
    return m.group(1) if m else ""


def setup_value(key):
    m = re.search(r"^" + re.escape(key) + r"=(.*)$", section("Setup"), re.M)
    return m.group(1).strip() if m else None


def netsh_params(sec):
    return [m.group(1).replace('""', '"') for m in re.finditer(r'Filename: "\{sys\}\\netsh\.exe"; Parameters: "(.*?)"; Flags',
                                                               section(sec))]


def test_setup_directives():
    assert setup_value("PrivilegesRequired") == "admin"
    assert setup_value("ArchitecturesAllowed") == "x64compatible"
    assert setup_value("ArchitecturesInstallIn64BitMode") == "x64compatible"
    assert setup_value("MinVersion") == "10.0.19045"
    assert setup_value("CloseApplications") == "yes"
    assert re.fullmatch(r"\{\{[0-9A-F-]{36}\}", setup_value("AppId"))
    assert setup_value("AppVersion") == "{#AppVersion}"
    assert setup_value("OutputBaseFilename") == "Wholecount-Setup-{#AppVersion}"
    assert setup_value("DefaultDirName") == r"{autopf}\Wholecount"


def test_publisher_default_equals_signing_json():
    publisher = json.loads((ROOT / "tools" / "signing.json").read_text(encoding="utf-8"))["publisher"]
    assert setup_value("AppPublisher") == "{#Publisher}"
    assert f'#define Publisher "{publisher}"' in ISS


def test_the_firewall_lines():
    run = netsh_params("Run")
    assert run == [
        'advfirewall firewall delete rule name="Wholecount offline (out)"',
        'advfirewall firewall delete rule name="Wholecount offline (in)"',
        'advfirewall firewall add rule name="Wholecount offline (out)" dir=out action=block '
        'program="{app}\\Wholecount.exe" enable=yes profile=any',
        'advfirewall firewall add rule name="Wholecount offline (in)" dir=in action=block '
        'program="{app}\\Wholecount.exe" enable=yes profile=any',
    ]
    assert netsh_params("UninstallRun") == run[:2]
    assert section("UninstallRun").count("RunOnceId") == 2


def test_the_launch_entry_drops_the_admin_token():
    line = next(ln for ln in section("Run").splitlines() if "Wholecount.exe\"; Description" in ln)
    assert "postinstall" in line and "nowait" in line and "skipifsilent" in line and "runasoriginaluser" in line


def test_no_network_use():
    assert "http" not in ISS.lower() and "DownloadTemporaryFile" not in ISS and "idp" not in ISS.lower().split()
    assert "[Languages]" not in ISS


def test_quoted_strings_follow_the_wording_rules():
    strings = re.findall(r"'([^']*)'", ISS) + re.findall(r'"([^"]*)"', ISS)
    for s in strings:
        assert EM_DASH not in s and "!" not in s, s
    assert "connects to nothing and downloads nothing" in section("Messages")


def test_geosupport_check_matches_m05():
    for d in GEOSUPPORT_DEFAULT_DIRS:
        assert f"DirExists('{d}')" in ISS
    assert "'GEOFILES'" in ISS and "Geosupport check: found" in ISS and "Geosupport check: not found" in ISS


def test_upgrades_remove_the_old_internal_folder():
    assert r'Name: "{app}\_internal"' in section("InstallDelete")
    assert "recursesubdirs ignoreversion" in section("Files")
