"""Helpers for M08 session tests: the R and S fixture in its base and decided states, and row lookups by Client_ID."""
from tests.fixtures.session import r_fixture
from wholecount.session import commands as C
from wholecount.session.runner import process


def base(tmp_path, **kw):
    s = r_fixture.session(tmp_path, **kw)
    process(s)
    return s


def rk(s, client_id, first=None):
    """The record key of the row with this Client_ID (and first name, when two rows share the ID)."""
    hits = [k for k, r in s.results.rows.items() if r.value("Client_ID") == client_id and (first is None or r.value("First_Name") == first)]
    assert hits, client_id
    return sorted(hits)[0]


def group(s, kind):
    return next(g for g in s.results.groups if g.kind == kind)


def decide_all(s):
    """The milestone's decided state: keep one identical, not copies, approved as entered, accept the fill, set R14 aside."""
    ident, poss, same = group(s, "identical"), group(s, "possible"), group(s, "same_id_different")
    s.history.execute(C.KeepOneInCopyGroup(ident.group_id, ident.members[0]))
    s.history.execute(C.MarkNotCopies(poss.group_id))
    s.history.execute(C.DecideSameIdConflict(same.group_id, "approved_as_entered"))
    s.history.execute(C.AcceptFills([rk(s, "R13")]))
    s.history.execute(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    return s


def decided(tmp_path, **kw):
    return decide_all(base(tmp_path, **kw))


def snapshot(s):
    r = s.results
    return (r.digest(), r.counts, partition(r))


def partition(r):
    """SPEC 7.3: clean rows, review rows (with Counted yes or no) and set-aside rows."""
    clean = frozenset(k for k, o in r.outcomes.items() if o.counted)
    review = frozenset((k, o.counted) for k, o in r.outcomes.items() if o.reasons and o.set_aside_reason is None)
    aside = frozenset(k for k, o in r.outcomes.items() if o.set_aside_reason is not None)
    return clean, review, aside
