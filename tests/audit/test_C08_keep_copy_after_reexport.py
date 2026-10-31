"""C-08: the old keep-one decision named a row by position, so a re-export kept the wrong copy. It names a record key."""
from tests.fixtures.session import r_fixture
from tests.support.session import base, group
from wholecount.session import commands as C
from wholecount.session.decisions import DecisionStore
from wholecount.session.runner import process


def test_same_record_kept_after_reorder(tmp_path):
    s = base(tmp_path / "a")
    g = group(s, "identical")
    s.history.execute(C.KeepOneInCopyGroup(g.group_id, g.members[1]))
    kept = g.members[1]
    s2 = r_fixture.session(tmp_path / "b", paths=r_fixture.files(tmp_path / "b", r=list(reversed(r_fixture.r_rows()))))
    s2.decisions = DecisionStore(s.decisions.snapshot())
    process(s2)
    assert s2.results.outcomes[kept].counted
    assert [k for k in g.members if s2.results.outcomes[k].set_aside_reason == "copy_of"] == [g.members[0]]
    assert (s2.results.kept, s2.results.lapsed) == (1, 0)


def test_changed_text_lapses_with_group_changed(tmp_path):
    s = base(tmp_path / "a")
    g = group(s, "identical")
    s.history.execute(C.KeepOneInCopyGroup(g.group_id, g.members[0]))
    rows = r_fixture.r_rows()
    gus = [i for i, r in enumerate(rows) if r[0] == "R07"]
    rows[gus[0]] = rows[gus[0]][:5] + ["brooklyn"] + rows[gus[0]][6:]
    s2 = r_fixture.session(tmp_path / "b", paths=r_fixture.files(tmp_path / "b", r=rows))
    s2.decisions = DecisionStore(s.decisions.snapshot())
    process(s2)
    assert [n.reason for n in s2.results.no_longer_apply] == ["group_changed"]
    assert any(x.kind == "identical" for x in s2.results.open_groups)
