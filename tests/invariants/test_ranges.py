"""SPEC 7.2: low <= high, final means one number, a same verdict lowers high by one and keeps low, and an open copy group of
two separate people widens the range by one."""
from tests.fixtures.session import r_fixture
from tests.support.session import base, decided
from wholecount.session import commands as C
from wholecount.session.runner import process


def test_ranges_and_final(tmp_path):
    s = decided(tmp_path)
    c = s.counts()
    assert c.goal1.low <= c.goal1.high and c.goal2.low <= c.goal2.high
    p = s.results.identity.proposals[0]
    s.history.execute(C.DecidePair(*p.pair, "same"))
    c2 = s.counts()
    assert (c2.goal1.high, c2.goal1.low) == (c.goal1.high - 1, c.goal1.low)
    for q in list(s.results.identity.proposals):
        s.history.execute(C.DecidePair(*q.pair, "different"))
    c3 = s.counts()
    assert c3.final and c3.goal1.single and c3.goal2.single


def test_open_copy_group_widens_by_one(tmp_path):
    rows = [["A1", "Ann", "North", "1980-01-01", "1 Oak St", "Brooklyn", "NY", "11201", "Housing"],
            ["A2", "Ann", "North", "1980-01-01", "1 Oak St", "Brooklyn", "NY", "11201", "Housing"]]
    s = r_fixture.session(tmp_path, paths=[r_fixture.write(tmp_path / "A.csv", rows)])
    process(s)
    c = s.counts()
    assert (c.goal1.low, c.goal1.high, c.open_copy_groups) == (1, 2, 1)
    assert base(tmp_path / "b").counts().goal1.low <= base(tmp_path / "c").counts().goal1.high
