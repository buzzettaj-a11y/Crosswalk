"""The old samples in tests/data/legacy_sample/, for reading only (P-GEO-4a)."""
from tests.conftest import ROOT
from tests.support.load import load

SAMPLES = ROOT / "tests" / "data" / "legacy_sample"
EXPECTED = {"clinic_export.csv": 62, "partner_export.tsv": 52, "legacy_export.xlsx": 57, "portal_export.json": 50,
            "state_export.xml": 45}


def test_legacy_samples_read():
    r = load(sorted(SAMPLES.iterdir()))
    rows = {f.name: f.accounting.included for f in r.files}
    assert rows == EXPECTED and sum(rows.values()) == 266
    assert all(f.status == "ok" and f.accounting.balanced() for f in r.files)
    assert all(t.kind == "records" and t.included and not t.sensitive_dropped for t in r.tables)
    clinic = next(t for t in r.tables if t.key.startswith("clinic"))
    assert clinic.key == "clinic_export_csv :: data :: 3380a5d7"
