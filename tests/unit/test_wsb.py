"""The Windows Sandbox template (M14 section 8): networking off, and every mapped path and the script exist."""
import xml.etree.ElementTree as ET

from tests.conftest import ROOT

TEMPLATE = ROOT / "tools" / "sandbox" / "wholecount-offline.wsb.in"


def fill(text, installer, results):
    return text.replace("@INSTALLER_DIR@", str(installer)).replace("@RESULTS_DIR@", str(results))


def check(xml_text):
    root = ET.fromstring(xml_text)
    problems = []
    if root.findtext("Networking") != "Disable":
        problems.append("networking")
    if root.findtext("vGPU") != "Disable":
        problems.append("vgpu")
    import pathlib
    for mf in root.iter("MappedFolder"):
        if not pathlib.Path(mf.findtext("HostFolder")).is_dir():
            problems.append("missing " + mf.findtext("SandboxFolder"))
    if "sandbox_run.ps1" not in (root.findtext("LogonCommand/Command") or ""):
        problems.append("script")
    return problems


def test_template_and_a_generated_file(tmp_path):
    installer, results = tmp_path / "in", tmp_path / "out"
    installer.mkdir()
    results.mkdir()
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "@INSTALLER_DIR@" in text and "@RESULTS_DIR@" in text
    assert check(fill(text, installer, results)) == []
    assert (ROOT / "tools" / "sandbox" / "sandbox_run.ps1").is_file()
    ro = [mf.findtext("ReadOnly") for mf in ET.fromstring(fill(text, installer, results)).iter("MappedFolder")]
    assert ro == ["true", "false"]


def test_negative_controls(tmp_path):
    text = fill(TEMPLATE.read_text(encoding="utf-8"), tmp_path / "nope", tmp_path)
    assert "missing C:\\Wholecount\\in" in check(text)
    assert "networking" in check(text.replace("<Networking>Disable</Networking>", "<Networking>Default</Networking>"))
