"""B-09 (High): a spaced hyphen in a Queens house number broke the address."""
from wholecount.engine.prepare.address import parse_address


def test_B09_both_forms_keep_the_house_number():
    assert parse_address("117 - 19 45th Ave").street == "117-19 45th Ave"
    a = parse_address("117 - 19 45th Ave, Flushing, NY 11355")
    assert (a.street, a.city, a.zip) == ("117-19 45th Ave", "Flushing", "11355")


def test_B09_a_spaced_dash_between_words_still_splits():
    a = parse_address("123 Main St - Apt 4 - Brooklyn")
    assert (a.street, a.unit) == ("123 Main St", "Apt 4")
