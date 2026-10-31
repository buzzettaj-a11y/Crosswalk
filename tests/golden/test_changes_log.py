"""tests/golden/CHANGES.md lists every proof-sheet answer the spec changed, with five cells per row and a rule ID."""
import re

from tests.conftest import ROOT


def rows():
    out = []
    for line in (ROOT / "tests" / "golden" / "CHANGES.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0] not in ("Sheet", "---"):
            out.append(cells)
    return out


def test_every_row_is_complete():
    rs = rows()
    assert rs
    for cells in rs:
        assert len(cells) == 5 and all(cells), cells
        assert re.fullmatch(r"P-[A-Z]+-[0-9]+", cells[4]), cells


def test_sheet_10_row_3_is_listed():
    assert any(c[0].startswith("10") and c[1] == "3" and c[4] == "P-PREP-4" for c in rows())
