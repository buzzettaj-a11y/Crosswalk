"""H13, C-04: any sequence of commands undone in full gives back the starting results."""
import pathlib
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.invariants.test_balance import actions
from tests.support.session import base, snapshot


@settings(max_examples=10, deadline=None)
@given(st.lists(st.integers(0, 7), max_size=4))
def test_undo_everything(seq):
    s = base(pathlib.Path(tempfile.mkdtemp()))
    start = snapshot(s)
    acts = actions(s)
    done = 0
    for i in seq:
        try:
            s.history.execute(acts[i]())
            done += 1
        except Exception:
            pass
    for _ in range(done):
        s.history.undo()
    assert snapshot(s) == start
