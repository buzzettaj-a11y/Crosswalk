"""P-MAP-1: mapping by meaning, by name only, never by column order."""
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.mapping import mapped
from wholecount.engine.mapping import ColumnRef, name_score
from wholecount.engine.schema import default_schema

S = default_schema()


def score(field, header):
    return name_score(S.get(field), ColumnRef(0, header))


def test_tiers():
    assert score("First_Name", "First Name") == 100 and score("First_Name", "first_name") == 100
    assert score("First_Name", "Forename") == 90 and score("Client_ID", "uid") == 90
    assert score("First_Name", "Client First Name") == 60 and score("Address_1", "Home Address") == 60
    assert score("First_Name", "Favorite Color") == 0


def test_camel_case_and_digits_split():
    assert score("First_Name", "FirstName") == 100 and score("Address_1", "Address1") == 100


def test_deny_groups():
    assert score("First_Name", "Emergency Contact First Name") == 0
    assert score("Last_Name", "Last Visit") == 0
    assert score("Address_1", "Employer Address") == 0
    assert score("City", "Birth City") == 0
    assert score("Client_ID", "Case ID") == 0 and score("Client_ID", "Household ID") == 0
    assert score("Program", "Program ID") == 0 and score("Program", "Program Start Date") == 0


def test_bare_words_match_only_whole_headers():
    assert score("First_Name", "First") == 90
    assert score("First_Name", "First Visit") == 0 and score("Last_Name", "Last Seen") == 0
    assert score("First_Name", "Caseworker First") == 0


def test_a_tie_gives_a_question_and_no_assignment():
    m = mapped(["Surname", "Family", "First Name"])
    assert "Last_Name" not in m.as_names()
    assert [(q.field, sorted(c.name for c in q.candidates)) for q in m.questions] == [("Last_Name", ["Family", "Surname"])]


def test_one_column_fills_one_role():
    names = mapped(["Address", "City", "State", "Zip", "First Name", "Last Name", "ID"]).as_names()
    assert len(set(names.values())) == len(names)


HEADERS = ["First Name", "Surname", "Client ID", "Home Address", "Apt", "City", "ST", "Zip Code", "Program", "DOB", "Mailing Address",
           "Last Visit", "Emergency Contact First Name", "Notes"]


@settings(max_examples=60, deadline=None)
@given(st.permutations(HEADERS))
def test_shuffling_columns_never_changes_the_mapping(order):
    assert mapped(list(order)).as_names() == mapped(HEADERS).as_names()
