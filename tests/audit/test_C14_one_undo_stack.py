"""C-14: the old Undo only popped group actions. One stack now covers every kind of change."""
from tests.support.session import base, rk, snapshot
from wholecount.session import commands as C


def test_three_undos_in_reverse(tmp_path):
    s = base(tmp_path)
    states = [snapshot(s)]
    s.history.execute(C.SendToRowByRow("name_missing"))
    states.append(snapshot(s))
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    states.append(snapshot(s))
    s.history.execute(C.SetAsideRows([rk(s, "R13")], "not_a_client"))
    for want in reversed(states):
        assert s.history.undo() is not None
        assert snapshot(s) == want
    assert s.history.undo() is None
