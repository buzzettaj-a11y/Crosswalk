"""Program groups from an earlier batch (M07 PROG-9, M13 XW-4)."""
from tests.support import crosswalk as X
from wholecount.session import commands as C


def test_a_confirmed_group_comes_back_and_a_batch_split_wins(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    names = sorted({n.name for n in s.results.program_names})[:2]
    s.history.execute(C.DecideProgramGroup("merge", tuple(names), "Combined"))
    X.download(s, tmp_path / "o1")
    two = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], day=1)
    X.run(two)
    groups = [g for g in two.results.program_map.groups if set(g.members) == set(names)]
    assert groups and groups[0].from_earlier_batch
    two.history.execute(C.DecideProgramGroup("split", tuple(names)))
    assert not [g for g in two.results.program_map.groups if set(g.members) == set(names)]
