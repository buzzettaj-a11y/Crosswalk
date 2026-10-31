"""H3 for reading: the same bytes read twice give the same keys and counts."""
from tests.conftest import ROOT
from tests.support.load import load


def snapshot(r):
    return ([(f.name, f.status, f.letter, f.accounting) for f in r.files],
            [(t.key, t.headers, t.rows, t.record_keys, t.kind, t.included) for t in r.tables])


def test_same_bytes_same_result():
    paths = sorted((ROOT / "tests" / "data" / "legacy_sample").iterdir())
    assert snapshot(load(paths)) == snapshot(load(paths))
