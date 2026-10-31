"""B-07 (High): a 9-digit ZIP inside an address was read as its last five digits."""
import pytest

from wholecount.engine.prepare.address import parse_address


@pytest.mark.parametrize("raw", ["123 Main St, Brooklyn, NY 112011234", "123 Main St Brooklyn NY 112011234", "123 Main St Brooklyn NY 11201-1234"])
def test_B07_nine_digits_give_the_first_five_and_a_note(raw):
    a = parse_address(raw)
    assert (a.street, a.city, a.state, a.zip) == ("123 Main St", "Brooklyn", "NY", "11201")
    assert a.notes == ["zip_had_9_digits"]


def test_B07_digits_inside_text_are_never_a_zip():
    assert parse_address("Apt 1120123 Main St").zip == ""
