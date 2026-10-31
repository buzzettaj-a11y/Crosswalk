"""C-04: the old Undo restored decisions but left the counts from before. Undo now recomputes before it returns."""
import pytest

from tests.support.session import base, decided, group, rk, snapshot
from wholecount.session import commands as C
from wholecount.session.reviewer import AcceptProof


def commands(s):
    return [
        C.ApproveRows([rk(s, "R14")], "name_missing"),
        C.AcceptGroup("name_missing", [rk(s, "R14")], AcceptProof(1, "checked_sample")),
        C.SetAsideRows([rk(s, "R01")], "test_record"),
        C.AcceptFills([rk(s, "R13")]),
        C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[1]),
        C.MarkNotCopies(group(s, "possible").group_id),
        C.DecideSameIdConflict(group(s, "same_id_different").group_id, "approved_as_entered"),
        C.DecideSameIdConflict(group(s, "same_id_different").group_id, "different_people"),
        C.KeepOnePerProgram(list(s.results.outcomes)),
        C.SendToRowByRow("name_missing"),
        C.ReturnToOpen([rk(s, "R14")]),
        C.DecidePair(*s.results.identity.proposals[0].pair, "same"),
        C.DecidePair(*s.results.identity.proposals[0].pair, "different"),
        C.DecideProgramGroup("confirm", ("Housing", "Youth")),
        C.AcknowledgeLowConfidence(),
        C.SetReviewer("Sam"),
    ]


@pytest.mark.parametrize("i", range(16))
def test_apply_then_undo_restores_everything(tmp_path, i):
    s = base(tmp_path)
    cmd = commands(s)[i]
    before = snapshot(s)
    s.history.execute(cmd)
    s.history.undo()
    assert snapshot(s) == before


def test_return_to_open_undo_on_the_decided_state(tmp_path):
    s = decided(tmp_path)
    before = snapshot(s)
    s.history.execute(C.ReturnToOpen([rk(s, "R14")]))
    assert snapshot(s) != before
    s.history.undo()
    assert snapshot(s) == before


def test_the_c04_case(tmp_path):
    s = base(tmp_path)
    before = snapshot(s)
    s.history.execute(C.DecideSameIdConflict(group(s, "same_id_different").group_id, "approved_as_entered"))
    assert s.counts().counted == 15
    s.history.undo()
    assert snapshot(s) == before and s.counts().counted == 13
