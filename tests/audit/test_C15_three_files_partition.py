"""C-15: the old review file held both review and set-aside rows, so the three files overlapped. They partition now (7.3)."""
import pytest

from tests.support.session import base, group, partition, rk
from wholecount.session import commands as C


def steps(s):
    return [lambda: C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0]),
            lambda: C.MarkNotCopies(group(s, "possible").group_id),
            lambda: C.DecideSameIdConflict(group(s, "same_id_different").group_id, "different_people"),
            lambda: C.AcceptFills([rk(s, "R13")]),
            lambda: C.ApproveRows([rk(s, "R14")], "name_missing"),
            lambda: C.SetAsideRows([rk(s, "R01")], "test_record")]


def check(r):
    clean, review, aside = partition(r)
    no = {k for k, counted in review if not counted}
    assert not clean & aside and not no & clean and not no & aside
    assert len(clean) + len(no) + len(aside) == r.counts.received
    assert {k for k, counted in review if counted} <= clean


def test_after_each_command(tmp_path):
    s = base(tmp_path)
    check(s.results)
    for make in steps(s):
        s.history.execute(make())
        check(s.results)
