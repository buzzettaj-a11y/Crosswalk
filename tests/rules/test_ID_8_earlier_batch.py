"""ID-8 and P-ID-3 earlier_batch: links from the saved crosswalk (M13). A person's link joins with a split action; a tool's link
that no longer holds lets go, and the key linked first keeps the saved master ID."""
import pytest

from tests.fixtures.people.builders import pair_of, prow
from wholecount.engine.identity import KnownMaster, PairVerdict, master_id, resolve

pytestmark = pytest.mark.claim("CL-ID-JOIN-03")


def rows():
    return [prow("a", "A", "1", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            prow("b", "B", "2", "Anna", "Pérez-Soto", "1990-05-07", "1 Far Rd", "10451")]


def test_an_inherited_same_verdict_is_an_earlier_batch_join():
    rs = rows()
    a, b = pair_of(rs, "a", "b")
    plain = resolve(rs)
    r = resolve(rs, [PairVerdict(a, b, "same", "old", "Joe", inherited=True)])
    assert [j.reason for j in r.auto_joins] == ["earlier_batch"] and r.settled == plain.settled - 1
    split = resolve(rs, [PairVerdict(a, b, "same", "old", "Joe", inherited=True), PairVerdict(a, b, "different", "new", "Joe")])
    assert split.auto_joins == () and split.settled == plain.settled


def test_a_reviewer_link_to_one_saved_master_joins():
    rs = rows()
    a, b = pair_of(rs, "a", "b")
    known = {a: KnownMaster("M-saved00001", "2025-01-01", "2025-01-01", "derived"),
             b: KnownMaster("M-saved00001", "2025-01-01", "2025-04-01", "reviewer")}
    r = resolve(rs, known=known)
    assert [j.reason for j in r.auto_joins] == ["earlier_batch"]
    assert r.master_of[a] == r.master_of[b] == "M-saved00001"


def test_a_tool_link_that_no_longer_holds_stays_two_groups():
    rs = rows()
    a, b = pair_of(rs, "a", "b")
    known = {a: KnownMaster("M-saved00001", "2025-01-01", "2025-04-01", "four_exact_facts"),
             b: KnownMaster("M-saved00001", "2025-01-01", "2025-01-01", "derived")}
    r = resolve(rs, known=known)
    assert r.auto_joins == () and r.settled == 2
    assert r.master_of[b] == "M-saved00001" and r.master_of[a] == master_id(a)
    assert r.released == ((a, "M-saved00001"),)
    assert r.master_of[a] != r.master_of[b]


def test_no_earlier_batch_without_known_or_inherited():
    assert all(j.reason != "earlier_batch" for j in resolve(rows()).auto_joins)
