"""P-READ-3, second half (B-24): a U+FFFD in a mapped value gives the soft reason unreadable_character, naming the field."""
from tests.support.std import ids, std


def test_unreadable_character():
    r = std(Last_Name="Pe�a")
    assert ids(r) == ["unreadable_character"] and r.value("Last_Name") == "Pe�a"
    assert [x.field for x in r.reasons] == ["Last_Name"] and r.count_status.counted
