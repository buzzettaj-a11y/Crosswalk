"""The five example files (P-GEO-4a) load exactly as the `files` section of EXPECTED.json plans, and the generator reproduces them."""
import json
import subprocess
import sys

import pytest

from tests.conftest import ROOT
from tests.support.load import load
from wholecount.engine.read.accounting import account_grid
from wholecount.engine.read.reader import read_path
from wholecount.engine.read.tables import find_tables, rebuild_with_header

pytestmark = pytest.mark.claim("CL-READ-ACCOUNTING-01")

DATA = ROOT / "wholecount" / "sample_data"
NAMES = ["example_clinic.csv", "example_housing.xlsx", "example_partner.tsv", "example_portal.json", "example_state.xml"]
EXPECTED = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result():
    return load([DATA / n for n in NAMES])


def test_every_file_loads_as_planned(result):
    assert [f.name for f in result.files] == NAMES and all(f.status == "ok" for f in result.files)
    for f in result.files:
        e = EXPECTED["files"][f.name]
        a = f.accounting
        tables = [t for t in result.tables if t.letter == f.letter]
        got = {
            "tables_found": len(tables), "tables_included": sum(t.included for t in tables), "rows_included": a.included,
            "rows_excluded": a.excluded, "rows_non_table": a.non_table, "rows_header": a.header,
            "rows_above_header": a.above_header, "rows_shared": a.shared_rows, "non_empty_rows": a.non_empty_rows,
            "balanced": a.balanced(), "sensitive_dropped": [h for t in tables for h in t.sensitive_dropped],
            "encoding": f.read_file.encoding,
        }
        assert got == {k: e[k] for k in got}, f.name
        assert [{"sheet": t.sheet, "kind": t.kind, "included": t.included, "header_row": t.header_row, "rows": len(t.rows)}
                for t in tables] == e["tables"], f.name


def test_workbook_header_needs_a_choice(result):
    e = EXPECTED["files"]["example_housing.xlsx"]
    clients = next(t for t in result.tables if t.sheet == "Clients")
    assert clients.header_warning == e["header_warning"] and clients.suggested_header_row == e["suggested_header_row"]
    notes = next(t for t in result.tables if t.sheet == "Notes")
    assert not notes.included and notes.kind != "records"


def test_workbook_after_the_planned_header_choice_balances():
    e = EXPECTED["files"]["example_housing.xlsx"]["after_header_choice"]
    rf = read_path(DATA / "example_housing.xlsx")
    grids = {g.sheet: g for g in rf.grids}
    gt = find_tables(grids["Clients"])
    t = rebuild_with_header(gt.tables[0], e["header_row"])
    assert (t.kind, t.included, len(t.rows), t.above_header_rows) == (e["kind"], e["included"], e["rows_included"], e["rows_above_header"])
    assert t.rows[-1][0] == "Total" and t.row_numbers[-1] == e["total_row"]
    assert account_grid(grids["Clients"], [t], gt.non_table_blocks).balanced()


@pytest.mark.claim("CL-READ-ENCODING-01")
def test_partner_file_is_windows_text_with_samples(result):
    f = next(f for f in result.files if f.name == "example_partner.tsv")
    assert f.read_file.encoding == "windows-1252" and 1 <= len(f.read_file.encoding_samples) <= 5


def test_twelve_rows_planned_without_an_identifier():
    assert EXPECTED["standardize"]["no_identifier_total"] == 12


def test_size_is_in_the_planned_range():
    received = EXPECTED["counts"]["before_decisions"]["rows_received"]
    assert 250 <= received <= 300


def test_generator_check_passes():
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "make_example_data.py"), "--check"], capture_output=True, text=True,
                       timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.splitlines() == ["files_compared 7", "files_differing 0", "reference_hash_registered 1"]
