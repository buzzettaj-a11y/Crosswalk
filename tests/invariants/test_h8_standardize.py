"""H8: no cell text from the canary file reaches an audit event or a dev command line."""
import csv
import subprocess
import sys

from tests.conftest import ROOT
from tests.support.std import TODAY, row_input
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.model import audit_events
from wholecount.engine.standardize.rows import TableOptions, standardize_row

CANARY = ROOT / "docs" / "audit" / "A-fixtures" / "canary_clients.csv"


def cells():
    out = set()
    for rec in csv.DictReader(CANARY.open(encoding="utf-8")):
        out |= {v for v in rec.values() if len(v) >= 4}
    return out


def test_no_cell_in_audit_events():
    schema = default_schema()
    for i, rec in enumerate(csv.DictReader(CANARY.open(encoding="utf-8"))):
        values = {k: v for k, v in rec.items() if k in ("Client_ID", "First_Name", "Last_Name", "Address_1", "City", "State", "Zip",
                                                         "Program")}
        values["Date_of_Birth"] = rec["DOB"]
        r = standardize_row(row_input(f"key{i:04d}", **values), schema, TableOptions(), TODAY)
        text = repr(audit_events(r))
        assert not [c for c in cells() if c in text]


def test_no_cell_in_dev_standardize_output():
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "standardize", str(CANARY), "--today", "2026-10-30"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert not any(c in p.stdout for c in cells())
