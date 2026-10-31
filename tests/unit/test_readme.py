"""README.md (M15): the four sentences of SPEC 12.5 as written, and a guarantees table whose test files exist."""
import re

from tests.conftest import ROOT

README = ROOT / "README.md"
LAYERS = ("Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5")


def _section(text, heading):
    return text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_spec_12_5_sentences_appear_as_written():
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    sentences = ["An administrator can remove the firewall rule.", "A managed computer can ignore local rules.",
                 "C and C++ code isn't seen by the audit hook. That covers Qt, libxml2 and the Geosupport DLL.",
                 "A mapped network drive looks like a local path."]
    text = _section(README.read_text(encoding="utf-8"), "What cannot be guaranteed")
    for s in sentences:
        assert s in spec
        assert s in text


def _guarantee_rows():
    table = _section(README.read_text(encoding="utf-8"), "The guarantees")
    return [line.split("|")[1:-1] for line in table.splitlines() if line.startswith("|") and "---" not in line][1:]


def test_every_layer_and_no_ai_has_a_row():
    layers = [row[1] for row in _guarantee_rows()]
    for layer in LAYERS:
        assert sum(layer in cell for cell in layers) == 1
    assert any("No AI" in cell for cell in layers)
    assert all(any(layer in cell for layer in LAYERS + ("No AI",)) for cell in layers)


def test_every_test_file_in_the_guarantees_table_exists():
    for row in _guarantee_rows():
        files = re.findall(r"`([^`]+)`", row[2])
        assert files
        for f in files:
            assert (ROOT / f).is_file(), f


def test_sections_are_in_the_milestone_order():
    text = README.read_text(encoding="utf-8")
    order = ["Install", "Run from source", "Build and release", "Tests", "Where things are", "The guarantees",
             "What cannot be guaranteed", "Licenses"]
    found = re.findall(r"^## (.+)$", text, re.M)
    assert found == order


def test_qt_notice_exists():
    assert "licenses/PySide6-LGPL-NOTICE.txt" in README.read_text(encoding="utf-8")
    assert (ROOT / "licenses" / "PySide6-LGPL-NOTICE.txt").is_file()
