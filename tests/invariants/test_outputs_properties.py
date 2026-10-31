"""Properties of the outputs: row counts equal their tables, the three row sets partition received rows, two runs with a fixed
clock are byte-identical, and random decisions never put a fixture value in a log."""
import pathlib
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.fixtures.outputs.fixture import VALUES, session
from tests.invariants.test_balance import actions
from tests.support.outputs import write
from wholecount.engine.outputs import tables
from wholecount.engine.outputs.review_file import manual_review_needed
from wholecount.engine.outputs.view import ExportSettings
from wholecount.session import commands as C
from wholecount.session.export import build_view


@settings(max_examples=8, deadline=None)
@given(st.lists(st.integers(0, 7), max_size=4))
def test_outputs_after_random_decisions(seq):
    tmp = pathlib.Path(tempfile.mkdtemp())
    s = session(tmp)
    acts = actions(s)
    for i in seq:
        try:
            s.history.execute(acts[i]())
        except Exception:
            pass
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    view = build_view(s)
    clean = {r["Record_Key"] for r in tables.final_clean_mapped(view, ExportSettings())}
    no = {r["Record_Key"] for r in manual_review_needed(view) if r["Counted"] == "No"}
    aside = {r["Record_Key"] for r in tables.set_aside_records(view, ExportSettings())}
    assert not clean & no and not clean & aside and not no & aside
    assert len(clean) + len(no) + len(aside) == s.counts().received
    receipt = write(s, tmp / "a")
    write(s, tmp / "b")
    for f in receipt.files:
        name = pathlib.Path(f.path).name
        if not name.endswith(".txt"):
            assert (tmp / "a" / name).read_bytes() == (tmp / "b" / name).read_bytes()
    for log in ("Internal_Audit_Log.txt", "Shareable_Audit_Log.txt"):
        text = (tmp / "a" / log).read_text(encoding="utf-8")
        assert not any(v in text for v in VALUES)
