"""A-22: the old ledger, summary and download each did their own arithmetic and disagreed. balance_lines is the one source."""
import pytest

from tests.support.session import base, group, rk
from wholecount import copy
from wholecount.engine.counts import balance_lines
from wholecount.session import commands as C

pytestmark = [pytest.mark.claim("CL-COUNT-05"), pytest.mark.claim("CL-COUNT-10")]


def check(s):
    s.counts()
    (rows_key, rows), (loc_key, loc) = balance_lines(s.results.balance)
    assert rows["received"] == rows["counted"] + rows["not_counted_yet"] + rows["set_aside"] == s.results.counts.received
    assert loc["counted"] == loc["mapped"] + loc["not_mapped"] == s.results.counts.counted
    assert copy.get(rows_key, **rows) and copy.get(loc_key, **loc)


def test_after_every_command(tmp_path):
    s = base(tmp_path)
    check(s)
    for cmd in (C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0]),
                C.AcceptFills([rk(s, "R13")]), C.SetAsideRows([rk(s, "R14")], "out_of_scope"),
                C.DecideSameIdConflict(group(s, "same_id_different").group_id, "approved_as_entered")):
        s.history.execute(cmd)
        check(s)
