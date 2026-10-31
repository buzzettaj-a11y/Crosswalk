"""The five example files through load, map, proposed steps and standardize. Per table, the counts and every planned problem row
equal the `standardize` section of EXPECTED.json."""
import json

import pytest

from tests.conftest import ROOT
from tests.support.load import load
from tests.support.std import TODAY
from wholecount.engine.dateorder import collect_evidence, decide
from wholecount.engine.mapping import auto_map, profile_columns
from wholecount.engine.prepare.steps import apply_steps, propose_steps
from wholecount.engine.read.tables import rebuild_with_header
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.dates import date_context
from wholecount.engine.standardize.inputs import build_inputs
from wholecount.engine.standardize.rows import TableOptions, standardize_table

DATA = ROOT / "wholecount" / "sample_data"
PLAN = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))
STD = PLAN["standardize"]
S = default_schema()
NAMES = [k for k in STD if k.startswith("example_")]


@pytest.fixture(scope="module")
def results():
    r = load([DATA / n for n in NAMES])
    names = {f.letter: f.name for f in r.files}
    out = {}
    for t in r.tables:
        e = PLAN["map"]["auto"][names[t.letter]]
        if e["sheet"] != t.sheet:
            continue
        if e.get("header_row"):
            t = rebuild_with_header(t, e["header_row"])
        m = auto_map(S, profile_columns(t), t.key)
        prep = apply_steps(t, propose_steps(t, m))
        m = auto_map(S, profile_columns(t, prep.column_refs()), t.key)
        dob = m.column_for("Date_of_Birth")
        meta = {} if dob.derived else {i: x for (i, c), x in t.meta.items() if c == dob.index}
        ctx = {"Date_of_Birth": date_context(decide(collect_evidence(prep.values(dob.name), meta)))}
        out[names[t.letter]] = standardize_table(build_inputs(prep, m, (), S), S, TableOptions(ctx), TODAY)
    return out


@pytest.mark.parametrize("name", NAMES)
def test_counts_and_planned_rows(results, name):
    rows, e = results[name], STD[name]
    statuses = [r.count_status.value for r in rows]
    assert len(rows) == e["rows_received"]
    assert sum(1 for r in rows if r.count_status.counted) == e["counted"]
    assert statuses.count("not_counted_yet") == e["not_counted_yet"] and statuses.count("set_aside") == e["set_aside"]
    got = [{"row": r.row_number, "reasons": sorted(set(r.reason_ids()))} for r in rows if r.reasons]
    assert got == e["planned_problem_rows"]
    assert [{"row": r.row_number, "reason": r.set_aside_reason} for r in rows if r.set_aside_reason] == e["planned_set_aside_rows"]
    by_row = {r.row_number: r for r in rows}
    for planned in e["planned_notes"]:
        assert set(planned["notes"]) <= {n.reason_id for n in by_row[planned["row"]].notes}, planned


def test_twelve_rows_without_an_identifier(results):
    assert sum(r.reason_ids().count("no_identifier") for rows in results.values() for r in rows) == STD["no_identifier_total"] == 12
