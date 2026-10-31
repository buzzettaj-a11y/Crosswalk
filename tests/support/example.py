"""The five example files through load, map, proposed steps and standardize, as M04's golden test runs them."""
import json

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
NAMES = [k for k in PLAN["standardize"] if k.startswith("example_")]


def standardized_example():
    """{file name: [StdRow, ...]} for the planned table of each example file."""
    schema = default_schema()
    r = load([DATA / n for n in NAMES])
    names = {f.letter: f.name for f in r.files}
    out = {}
    for t in r.tables:
        e = PLAN["map"]["auto"][names[t.letter]]
        if e["sheet"] != t.sheet:
            continue
        if e.get("header_row"):
            t = rebuild_with_header(t, e["header_row"])
        m = auto_map(schema, profile_columns(t), t.key)
        prep = apply_steps(t, propose_steps(t, m))
        m = auto_map(schema, profile_columns(t, prep.column_refs()), t.key)
        dob = m.column_for("Date_of_Birth")
        meta = {} if dob.derived else {i: x for (i, c), x in t.meta.items() if c == dob.index}
        ctx = {"Date_of_Birth": date_context(decide(collect_evidence(prep.values(dob.name), meta)))}
        out[names[t.letter]] = standardize_table(build_inputs(prep, m, (), schema), schema, TableOptions(ctx), TODAY)
    return out
