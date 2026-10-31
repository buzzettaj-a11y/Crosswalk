"""The five example files, through the proposed tidy-up steps and the M02 mapper, give `map.after_steps` in EXPECTED.json."""
import json

import pytest

from tests.conftest import ROOT
from tests.support.load import load
from wholecount.engine.mapping import auto_map, process_blocks, profile_columns
from wholecount.engine.prepare.steps import apply_steps, propose_steps, source_cells_changed
from wholecount.engine.read.tables import rebuild_with_header
from wholecount.engine.schema import default_schema

DATA = ROOT / "wholecount" / "sample_data"
PLAN = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))["map"]
AFTER = PLAN["after_steps"]
S = default_schema()


@pytest.fixture(scope="module")
def tables():
    r = load([DATA / n for n in AFTER])
    names = {f.letter: f.name for f in r.files}
    out = {}
    for t in r.tables:
        e = PLAN["auto"][names[t.letter]]
        if e["sheet"] != t.sheet:
            continue
        out[names[t.letter]] = rebuild_with_header(t, e["header_row"]) if e.get("header_row") else t
    return out


@pytest.mark.parametrize("name", list(AFTER))
def test_after_steps(tables, name):
    t = tables[name]
    before = [list(r) for r in t.rows]
    steps = propose_steps(t, auto_map(S, profile_columns(t), t.key))
    assert [{"kind": s.kind, "column": s.params["column"]} for s in steps] == AFTER[name]["steps"]
    prepared = apply_steps(t, steps)
    profiles = profile_columns(t, prepared.column_refs())
    m = auto_map(S, profiles, t.key)
    assert m.as_names() == AFTER[name]["fields"]
    assert [b.field for b in process_blocks(S, {t.key: m}, (), {t.key: profiles})] == AFTER[name]["blockers"]
    assert source_cells_changed(before, t) == 0
