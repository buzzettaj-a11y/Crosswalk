"""C-02: the old app joined two different people who shared a Client ID in one system. Now that's a copy group a person
decides, and identity treats the decided rows by the decision (P-DUP-3, ID-5)."""
import pytest

from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import ApprovedAsEntered, DifferentPeople, TableInfo, apply_copy_decision, find_copies, key_modes
from wholecount.engine.identity import PairVerdict, resolve

T = {"one": TableInfo(True, "one.csv")}

pytestmark = pytest.mark.claim("CL-ID-EV-14")


def fixture1():
    return [crow("r1", "one", "one.csv", "77", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("r2", "one", "one.csv", "77", "Beth", "Perez", "1994-09-09", "55 Oak Ave", "11201"),
            crow("r3", "one", "one.csv", "78", "Carl", "Ng", "1970-01-01", "1 Pine St", "11201")]


def decide(rows, decision):
    (g,) = [g for g in find_copies(rows, T) if g.kind == "same_id_different"]
    out = apply_copy_decision(g, decision)
    modes = key_modes([g], {g.group_id: decision}, rows=rows)
    people = [to_person(c, modes) for c in rows]
    k = {p.record_key: p.person_key for p in people}
    verdicts = [PairVerdict(k[a], k[b], v, "d1", "Joe") for a, b, v in out.verdict_pairs]
    return people, resolve(people, verdicts)


def test_fixture_1_one_group_before_a_decision():
    groups = find_copies(fixture1(), T)
    assert [(g.kind, g.members) for g in groups] == [("same_id_different", ("r1", "r2"))]


def test_fixture_1_approved_as_entered():
    _, r = decide(fixture1(), ApprovedAsEntered())
    assert r.auto_joins == ()
    assert [(p.band, [e.code for e in p.evidence if e.code == "same_system_id_differs"]) for p in r.proposals] == [
        ("possible", ["same_system_id_differs"])]
    assert (r.settled, r.low) == (3, 2)


def test_fixture_1_different_people():
    _, r = decide(fixture1(), DifferentPeople())
    assert r.proposals == () and (r.settled, r.low) == (3, 3)


def fixture2():
    return [crow("m1", "one", "one.csv", "500", "Maria", "Lopez", "", "100 Grand Concourse", "10451"),
            crow("m2", "one", "one.csv", "500", "Maria", "Garcia", "", "5 Main St", "11201")]


def test_fixture_2_marriage_and_a_move():
    assert decide(fixture2(), ApprovedAsEntered())[1].settled == 2
    assert decide(fixture2(), ApprovedAsEntered())[1].low == 1
    assert (decide(fixture2(), DifferentPeople())[1].settled, decide(fixture2(), DifferentPeople())[1].low) == (2, 2)


def test_fixture_3_same_person_two_addresses_is_one_record():
    rows = [crow("p1", "one", "one.csv", "9", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("p2", "one", "one.csv", "9", "Ana", "Perez", "1990-05-06", "9 Oak Ave", "11201")]
    assert [g for g in find_copies(rows, T) if g.kind == "same_id_different"] == []
    r = resolve([to_person(c) for c in rows])
    assert [(j.pair, j.reason) for j in r.auto_joins] == [(("p1", "p2"), "same_system_id")]
    assert r.settled == 1
