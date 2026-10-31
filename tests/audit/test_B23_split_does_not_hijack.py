"""B-23 (High): columns a tidy-up step made silently replaced the real name and address columns (P-MAP-3)."""
from tests.support.mapping import derived_ref, mapped

V = ["a", "b", "c"]


def test_B23_real_names_beat_a_split_of_caseworker_name():
    d = [(derived_ref("Caseworker Name_first", "Caseworker Name"), V), (derived_ref("Caseworker Name_last", "Caseworker Name", index=101), V)]
    m = mapped(["First Name", "Last Name", "Client ID", "Caseworker Name"], derived=d).as_names()
    assert m["First_Name"] == "First Name" and m["Last_Name"] == "Last Name"


def test_B23_real_street_beats_a_split_of_employer_address():
    d = [(derived_ref("Employer Address_street", "Employer Address"), V)]
    m = mapped(["First Name", "Last Name", "Client ID", "Street Address", "Employer Address"], derived=d).as_names()
    assert m["Address_1"] == "Street Address"


def test_B23_with_no_real_names_the_derived_pair_is_offered():
    d = [(derived_ref("Name_first", "Name"), V), (derived_ref("Name_last", "Name", index=101), V)]
    m = mapped(["Name", "Client ID"], derived=d).as_names()
    assert m["First_Name"] == "Name_first" and m["Last_Name"] == "Name_last"


def test_B23_a_split_of_the_chosen_address_column_replaces_it():
    d = [(derived_ref("Address_street", "Address"), V), (derived_ref("Address_city", "Address", index=101), V)]
    m = mapped(["First Name", "Last Name", "Client ID", "Address"], derived=d).as_names()
    assert m["Address_1"] == "Address_street" and m["City"] == "Address_city"


def test_B23_an_operator_pick_of_a_derived_column_is_honored():
    ref = derived_ref("Caseworker Name_first", "Caseworker Name")
    m = mapped(["First Name", "Last Name", "Client ID", "Caseworker Name"], derived=[(ref, V)])
    picked = m.with_choice("First_Name", ref)
    assert picked.as_names()["First_Name"] == "Caseworker Name_first"
    assert next(a for a in picked.assignments if a.field == "First_Name").chosen
