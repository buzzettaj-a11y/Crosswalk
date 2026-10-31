"""C-07: the old run and the program preview cleared every decision. A run now replays them by record key."""
from tests.support.session import base, group, rk
from wholecount.engine.programs import StopAtPrograms
from wholecount.session import commands as C
from wholecount.session.decisions import make
from wholecount.session.runner import fast_path, preview_counts, process


def test_four_decisions_survive_process_preview_and_fast_path(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0]))
    s.history.execute(C.MarkNotCopies(group(s, "possible").group_id))
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    s.history.execute(C.SetAsideRows([rk(s, "R13")], "out_of_scope"))
    decisions, counts = s.decisions.snapshot(), s.counts()
    for step in (process, lambda x: preview_counts(x, [make("program", (), "x", x.now_iso(), "Joe",
                                                                detail=(("program_kind", "confirm"),))]), fast_path):
        out = step(s)
        assert not isinstance(out, StopAtPrograms)
        assert s.decisions.snapshot() == decisions
        assert (s.results.kept, s.results.lapsed) == (4, 0)
        assert s.counts() == counts
