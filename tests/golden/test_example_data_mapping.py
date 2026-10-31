"""The five example files map as the `map.auto` section of EXPECTED.json plans, before any tidy-up step."""
import json

import pytest

from tests.conftest import ROOT
from tests.support.load import load
from wholecount.engine.mapping import auto_map, process_blocks, profile_columns
from wholecount.engine.read.tables import rebuild_with_header
from wholecount.engine.schema import default_schema

DATA = ROOT / "wholecount" / "sample_data"
EXPECTED = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))["map"]["auto"]
S = default_schema()


@pytest.fixture(scope="module")
def tables():
    r = load([DATA / n for n in EXPECTED])
    names = {f.letter: f.name for f in r.files}
    out = {}
    for t in r.tables:
        e = EXPECTED[names[t.letter]]
        if e["sheet"] != t.sheet:
            continue
        if e.get("header_row"):
            t = rebuild_with_header(t, e["header_row"])
        out[names[t.letter]] = t
    return out


@pytest.mark.parametrize("name", list(EXPECTED))
def test_auto_mapping_and_blockers(tables, name):
    t = tables[name]
    p = profile_columns(t)
    m = auto_map(S, p, t.key)
    assert m.as_names() == EXPECTED[name]["fields"]
    assert not m.questions
    blocks = process_blocks(S, {t.key: m}, (), {t.key: p})
    assert [b.field for b in blocks] == EXPECTED[name]["blockers"]
    assert all(b.field not in ("City", "State", "Zip", "Client_ID") for b in blocks)
