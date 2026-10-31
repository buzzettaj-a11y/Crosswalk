"""C-17: Client IDs are scoped to their system. Numbering 1 to 20 in three systems is 60 people, and one person enrolled twice
under one ID in one system is one person."""
from tests.fixtures.people.builders import crow, to_person
from wholecount.engine.copies import TableInfo, find_copies
from wholecount.engine.identity import resolve

FIRST = ["Ada", "Ben", "Cara", "Devi", "Evan", "Faye", "Gus", "Hana", "Ivo", "Jae"]
LAST = ["Alvarez", "Brown", "Chen", "Diaz", "Evans", "Fox", "Gupta", "Hill", "Ito", "Jones"]


def people(system, offset):
    out = []
    for i in range(20):
        k = offset + i
        out.append(crow(f"{system}{i:02d}", system, system, str(i + 1), FIRST[k % 10], LAST[(k // 10) % 10] + chr(97 + k % 7) * 2,
                        f"19{50 + k % 40}-0{1 + k % 9}-1{k % 9}", f"{100 + k} Test St", "11201", "Housing"))
    return out


def test_three_systems_numbered_1_to_20_are_60_people():
    rows = people("A", 0) + people("B", 20) + people("C", 40)
    t = {s: TableInfo(True, s) for s in "ABC"}
    assert find_copies(rows, t) == []
    r = resolve([to_person(c) for c in rows])
    assert r.proposals == () and r.auto_joins == () and r.settled == 60


def test_enrollment_file_one_person_per_id():
    rows = []
    for cid, first, last, dob, n in (("7", "Ana", "Perez", "1990-05-06", 7), ("8", "Bo", "Lee", "1991-01-01", 8),
                                     ("9", "Cy", "Kim", "1992-02-02", 9)):
        for prog in ("Housing", "Youth"):
            rows.append(crow(f"e{cid}{prog[0]}", "e", "enroll", cid, first, last, dob, f"{n} Elm St", "11201", prog))
    assert find_copies(rows, {"e": TableInfo(True, "enroll")}) == []
    r = resolve([to_person(c) for c in rows])
    assert [j.reason for j in r.auto_joins] == ["same_system_id"] * 3
    assert r.settled == 3
