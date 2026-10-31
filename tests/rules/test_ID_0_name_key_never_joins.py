"""ID-0 (SPEC 5.1, H5): a person key built from a name never joins rows by itself. Only a decision makes them one record."""
import pytest

from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import NotCopies, TableInfo, Unresolvable, apply_copy_decision, find_copies, key_modes
from wholecount.engine.identity import InconsistentInput, PairVerdict, PersonRow, resolve


def two(table_b="t2", cid=""):
    return [crow("r1", "t1", "S", cid, "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("r2", table_b, "S", cid, "Ana", "Perez", "1990-05-06", "9 Oak Ave", "10451")]


def test_two_tables_meet_as_a_likely_proposal():
    rows = two()
    modes = key_modes([], {}, rows=rows)
    assert modes == {"r1": "row", "r2": "row"}
    people = [to_person(c, modes) for c in rows]
    r = resolve(people)
    assert r.auto_joins == () and r.settled == 2
    (p,) = r.proposals
    assert (p.score, p.band) == (98, "likely")


def test_one_table_is_a_possible_copy_group_and_not_copies_is_accepted():
    rows = two("t1")
    (g,) = find_copies(rows, {"t1": TableInfo(True, "S")})
    assert g.kind == "possible"
    out = apply_copy_decision(g, NotCopies())
    modes = key_modes([g], {g.group_id: NotCopies()}, rows=rows)
    people = [to_person(c, modes) for c in rows]
    k = {p.record_key: p.person_key for p in people}
    r = resolve(people, [PairVerdict(k[a], k[b], v) for a, b, v in out.verdict_pairs])
    assert r.settled == 2 and r.proposals == () and r.low == 2


def test_a_client_id_key_is_still_one_record_and_not_copies_is_refused():
    rows = two("t1", cid="77")
    (g,) = find_copies(rows, {"t1": TableInfo(True, "S")})
    with pytest.raises(Unresolvable) as e:
        apply_copy_decision(g, NotCopies())
    assert e.value.code == "same_person_key"
    r = resolve([to_person(c) for c in rows])
    assert r.settled == 1 and [j.reason for j in r.auto_joins] == ["same_system_id"]


def test_undecided_rows_under_one_name_key_raise():
    rows = [PersonRow("r1", "k", "S", "", "Ana", "Perez", "1990-05-06", ""), PersonRow("r2", "k", "S", "", "Ana", "Perez", "1990-05-06", "")]
    with pytest.raises(InconsistentInput) as e:
        resolve(rows)
    assert e.value.code == "name_key_shared"
