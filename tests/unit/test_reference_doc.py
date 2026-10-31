"""docs/REFERENCE_DATA.md (SPEC 17 Q3, P-GEO-4): its folder path is the one the code reads, it names every header M05
accepts, and it says the sample file is refused."""
import re

from tests.conftest import ROOT
from wholecount import paths
from wholecount.brand import PRODUCT_NAME
from wholecount.engine.geo.reference import HEADERS

DOC = ROOT / "docs" / "REFERENCE_DATA.md"


def folder_in(text):
    """The Windows folder the document names, as the code would build it with LOCALAPPDATA set to that variable."""
    m = re.search(r"`%LOCALAPPDATA%((?:\\[^`\\]+)+)\\`", text)
    return m and m.group(1).strip("\\").split("\\")


def code_folder():
    d = paths.reference_dir(platform="win32", env={"LOCALAPPDATA": "BASE"})
    return list(d.parts[1:])


def test_folder_path_equals_the_source_constant():
    assert code_folder() == [PRODUCT_NAME, "reference"]
    assert folder_in(DOC.read_text(encoding="utf-8")) == code_folder()


def test_a_changed_path_is_caught(tmp_path):
    """Negative control: a temp copy with another folder fails the same comparison."""
    bad = DOC.read_text(encoding="utf-8").replace("\\Wholecount\\reference\\", "\\Wholecount\\references\\")
    assert folder_in(bad) != code_folder()


def test_names_every_accepted_header():
    text = DOC.read_text(encoding="utf-8")
    for aliases in HEADERS.values():
        for a in aliases:
            assert f"`{a}`" in text, a


def test_says_the_sample_file_is_refused():
    text = DOC.read_text(encoding="utf-8")
    assert "sample file" in text and "is refused for your own files" in text
    assert "none is used" in text
