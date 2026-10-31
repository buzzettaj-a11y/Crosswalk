"""H4: after any sequence of commands, both table equations and the batch equation hold."""
import pathlib
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.session import base, group, rk
from wholecount.engine.counts import assert_balance
from wholecount.session import commands as C


def actions(s):
    return [lambda: C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[1]),
            lambda: C.MarkNotCopies(group(s, "possible").group_id),
            lambda: C.DecideSameIdConflict(group(s, "same_id_different").group_id, "approved_as_entered"),
            lambda: C.AcceptFills([rk(s, "R13")]),
            lambda: C.SetAsideRows([rk(s, "R14")], "out_of_scope"),
            lambda: C.ApproveRows([rk(s, "R14")], "name_missing"),
            lambda: C.ReturnToOpen([rk(s, "R14")]),
            lambda: C.SetAsideRows([rk(s, "S1")], "duplicate_other_system")]


@settings(max_examples=12, deadline=None)
@given(st.lists(st.integers(0, 7), max_size=5))
def test_balance_after_every_step(seq):
    s = base(pathlib.Path(tempfile.mkdtemp()))
    acts = actions(s)
    for i in seq:
        try:
            s.history.execute(acts[i]())
        except Exception as e:  # a refused command (e.g. its group is already decided) changes nothing
            assert type(e).__name__ in ("Refused", "BulkAcceptRefused", "Unresolvable"), e
        assert_balance(s.results.balance, s.results.outcomes.values())
        c = s.counts()
        assert c.received == c.counted + c.not_counted_yet + c.set_aside
        assert c.counted == c.locations.mapped + c.locations.not_mapped
