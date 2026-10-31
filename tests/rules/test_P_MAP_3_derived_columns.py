"""P-MAP-3: a column made by a tidy-up step fills a field only when no real column scores for it, or when it was split from the
column the real mapping chose."""
from tests.support.mapping import derived_ref, mapped

V = ["a", "b", "c"]


def test_a_derived_column_is_not_used_while_a_real_one_scores():
    d = [(derived_ref("Notes_zip", "Notes"), V)]
    assert mapped(["Zip", "Notes"], derived=d).as_names() == {"Zip": "Zip"}


def test_derived_fills_an_unscored_field():
    d = [(derived_ref("Notes_zip", "Notes"), V)]
    assert mapped(["Notes"], derived=d).as_names() == {"Zip": "Notes_zip"}


def test_a_split_of_the_chosen_column_replaces_it():
    d = [(derived_ref("Full_Address_street", "Full_Address"), V)]
    assert mapped(["Full_Address"], derived=d).as_names() == {"Address_1": "Full_Address_street"}


def test_alternatives_include_the_derived_column():
    d = [(derived_ref("Notes_zip", "Notes"), V)]
    m = mapped(["Zip", "Notes"], derived=d)
    assert [c.name for c in m.assignments[0].alternatives] == ["Notes_zip"]
