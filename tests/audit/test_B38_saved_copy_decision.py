"""B-38: the old group ID hashed only the shared key, so a decision kept applying after a new row joined the group."""
from tests.fixtures.people.builders import crow
from wholecount.engine.copies import KeepOne, TableInfo, apply_copy_decision, find_copies

T = {"t": TableInfo(True, "S")}


def r(key):
    return crow(key, "t", "S", "", "Ana", "Perez", "1990-03-04", "7 Elm St", "11201", "Housing")


def test_a_new_member_changes_the_group_id():
    (g1,) = find_copies([r("row1"), r("row2")], T)
    decisions = {g1.group_id: KeepOne("row1")}
    assert apply_copy_decision(g1, decisions[g1.group_id]).set_aside == (("row2", "row1"),)
    (g2,) = find_copies([r("row1"), r("row2"), r("row3")], T)
    assert g2.group_id != g1.group_id and g2.group_id not in decisions
    assert g2.members == ("row1", "row2", "row3")
