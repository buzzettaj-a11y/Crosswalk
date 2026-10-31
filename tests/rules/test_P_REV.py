"""Review (SPEC 8, M08 REV-1 to REV-5) and corrections."""
import pytest

from tests.support.session import base, group, rk
from wholecount.engine.copies import CopyGroup
from wholecount.engine.review import RowOutcome, causes, finish_gate, keep_one_per_program
from wholecount.engine.standardize.model import CountStatus
from wholecount.session import commands as C


def test_REV_1_each_decision_kind(tmp_path):
    s = base(tmp_path)
    o = lambda cid, first=None: s.results.outcomes[rk(s, cid, first)]  # noqa: E731
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    assert o("R14").count_status == CountStatus.COUNTED_APPROVED and not o("R14").reasons
    s.history.execute(C.SetAsideRows([rk(s, "R01")], "not_a_client"))
    assert o("R01").set_aside_reason == "not_a_client"
    s.history.execute(C.AcceptFills([rk(s, "R13")]))
    assert o("R13").location.filled and o("R13").location.kind == "mapped" and not o("R13").reasons
    g = group(s, "identical")
    s.history.execute(C.KeepOneInCopyGroup(g.group_id, g.members[1]))
    assert s.results.outcomes[g.members[0]].set_aside_reason == "copy_of"
    assert s.results.outcomes[g.members[0]].kept_record_key == g.members[1]
    s.history.execute(C.DecideSameIdConflict(group(s, "same_id_different").group_id, "different_people"))
    assert o("R11", "Ivy").counted and o("R11", "Jon").counted


def test_REV_1_set_aside_needs_a_listed_reason_and_a_note_only_for_other():
    with pytest.raises(C.Refused):
        C.SetAsideRows(["k"], "because")
    with pytest.raises(C.Refused):
        C.SetAsideRows(["k"], "test_record", note="x")
    C.SetAsideRows(["k"], "other", note="short note")


def test_REV_2_tabs_and_ordering(tmp_path):
    s = base(tmp_path)
    from wholecount.session.runner import causes_for
    cs = causes_for(s.results)
    counts_tab = [(c.cause_id, c.count) for c in cs if c.tab == "counts"]
    assert counts_tab == [("copies_identical", 2), ("copies_possible", 2), ("same_id_conflict", 2), ("name_missing", 1)]
    assert [(c.cause_id, c.kind) for c in cs if c.tab == "location"] == [("address_part_missing", "fill_from_street")]


def test_REV_3_keep_one_per_program_touches_copy_groups_only():
    groups = [CopyGroup("g", "possible", "P-DUP-2", ("a", "b", "c")), CopyGroup("s", "same_id_different", "P-DUP-3", ("x", "y"))]
    r = keep_one_per_program({"a", "b", "c", "x", "z"}, groups, {"a": "H", "b": "H", "c": "Y"})
    assert r.kept == ("a", "c") and r.set_aside == (("b", "a"),) and r.left_alone == ("x", "z")


def test_REV_4_bulk_is_one_command_one_entry(tmp_path):
    s = base(tmp_path)
    keys = [rk(s, "R01"), rk(s, "R02"), rk(s, "R03")]
    n = len(s.audit)
    s.history.execute(C.SetAsideRows(keys, "test_record"))
    assert len(s.history.stack) == 1 and len(s.audit) == n + 1 and s.audit[-1].get("count") == [3]
    assert len([d for d in s.decisions if d.kind == "set_aside"]) == 3


def test_REV_5_finish_gate():
    open_row = RowOutcome("r", "t", 2, CountStatus.NOT_COUNTED_YET, None, ("name_missing",))
    loc_row = RowOutcome("l", "t", 3, CountStatus.COUNTED_PASSED, None, ("zip_not_valid",))
    assert finish_gate([open_row, loc_row]).held
    g = finish_gate([open_row, loc_row], routed={"name_missing"})
    assert not g.held and g.open_rows == 1
    assert not finish_gate([loc_row]).held
    assert finish_gate([loc_row], [CopyGroup("g", "possible", "P-DUP-2", ("l", "m"))]).held


def test_corrections_replay_after_process(tmp_path):
    from wholecount.engine.corrections import VerifiedCorrection
    from wholecount.session.runner import process

    s = base(tmp_path)
    s.history.execute(C.ApplyCorrections([VerifiedCorrection(rk(s, "R13"), (("Zip", "11201"),))], "f" * 64))
    process(s)
    assert s.results.outcomes[rk(s, "R13")].count_status == CountStatus.COUNTED_CORRECTED
    s.correction_texts.clear()
    process(s)
    assert [n.reason for n in s.results.no_longer_apply] == ["file_removed"]


def test_approve_never_closes_a_same_id_conflict(tmp_path):
    s = base(tmp_path)
    ivy, jon = rk(s, "R11", "Ivy"), rk(s, "R11", "Jon")
    with pytest.raises(C.Refused):
        C.ApproveRows([ivy], "same_id_conflict")
    s.history.execute(C.ApproveRows([ivy, jon, rk(s, "R14")], "*"))
    assert s.results.outcomes[ivy].count_status == CountStatus.NOT_COUNTED_YET
    assert "same_id_conflict" in s.results.outcomes[ivy].reasons
    assert s.results.outcomes[rk(s, "R14")].counted
