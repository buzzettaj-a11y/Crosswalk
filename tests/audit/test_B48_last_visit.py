"""B-48 (Medium): "Last Visit" was mapped as Last_Name when it came before "Surname"."""
from tests.support.mapping import mapped


def test_B48_last_visit_never_maps_a_name():
    for cols in (["First Name", "Last Visit", "Surname"], ["Surname", "Last Visit", "First Name"]):
        assert mapped(cols).as_names() == {"First_Name": "First Name", "Last_Name": "Surname"}


def test_B48_forename_and_surname_alone():
    assert mapped(["Forename", "Surname"]).as_names() == {"First_Name": "Forename", "Last_Name": "Surname"}
