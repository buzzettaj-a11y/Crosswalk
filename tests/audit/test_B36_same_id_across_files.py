"""B-36: the old same-ID check ran across every file, so system A's 1001 and system B's 1001 looked like one person."""
from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import TableInfo, find_copies
from wholecount.engine.identity import resolve

T = {"a": TableInfo(True, "A.csv"), "b": TableInfo(True, "B.csv")}


def test_same_id_in_two_systems_is_never_looked_at():
    rows = [crow("a1", "a", "A.csv", "1001", "Maria", "Lopez", "1980-01-01", "1 Oak St", "11201"),
            crow("b1", "b", "B.csv", "1001", "John", "Chen", "1970-02-02", "9 Pine St", "10001")]
    assert find_copies(rows, T) == []
    r = resolve([to_person(c) for c in rows])
    assert r.auto_joins == () and r.proposals == () and r.settled == 2


def test_same_id_in_one_system_with_two_people_is_a_group():
    rows = [crow("a1", "a", "A.csv", "1001", "Maria", "Lopez", "1980-01-01", "1 Oak St", "11201"),
            crow("a2", "a", "A.csv", "1001", "John", "Chen", "1970-02-02", "9 Pine St", "10001")]
    assert [g.kind for g in find_copies(rows, T)] == ["same_id_different"]
