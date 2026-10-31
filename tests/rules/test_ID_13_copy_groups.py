"""ID-13 (P-VAL-3, SPEC 7.2): an open copy group is left to P-DUP. Its rows stay counted, and the range covers it."""
import pytest

from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import NotCopies, TableInfo, apply_copy_decision, find_copies, key_modes
from wholecount.engine.identity import PairVerdict, resolve

pytestmark = pytest.mark.claim("CL-DUP-04")


def setup():
    rows = [crow("r1", "t", "S", "1", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("r2", "t", "S", "2", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", "", "", Note="x")]
    (g,) = find_copies(rows, {"t": TableInfo(True, "S")})
    return rows, g


def test_open_group_no_join_no_proposal_and_a_range():
    rows, g = setup()
    assert g.kind == "possible"
    people = [to_person(c, key_modes([g], {}, rows=rows)) for c in rows]
    r = resolve(people, open_copy_groups=[g.members])
    assert r.auto_joins == () and r.proposals == ()
    assert (r.settled, r.low) == (2, 1)


def test_after_not_copies_low_counts_two():
    rows, g = setup()
    out = apply_copy_decision(g, NotCopies())
    people = [to_person(c) for c in rows]
    k = {p.record_key: p.person_key for p in people}
    r = resolve(people, [PairVerdict(k[a], k[b], v) for a, b, v in out.verdict_pairs])
    assert (r.settled, r.low) == (2, 2)
