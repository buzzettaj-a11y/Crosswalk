"""B-06 (High): the calculated ZIP kept the first five digits of garbage. Now only a valid NYC ZIP is ever written."""
import pytest

from tests.support.zips import DictResolver
from wholecount.engine.prepare.calc_zip import calculate

NO_STREET_LOOKUP = DictResolver({})


@pytest.mark.parametrize("bad", ["112019", "11201 7", "11201-12", "123456789012", "1 1 2 0 1", "11201abc", "99999-0000", "1120", "07030"])
def test_B06_garbage_gives_a_blank_never_five_digits(bad):
    assert calculate("1 Nowhere Pl", "Brooklyn", bad, "blanks", NO_STREET_LOOKUP) == ("", "zip_not_worked_out")


@pytest.mark.parametrize("good", ["11201-1234", "11201", "112011234"])
def test_B06_valid_nyc_zip_is_kept(good):
    assert calculate("1 Nowhere Pl", "Brooklyn", good, "blanks", NO_STREET_LOOKUP) == ("11201", "zip_kept")


def test_B06_a_resolver_answer_outside_nyc_is_discarded():
    r = DictResolver({("9 Elm St", "Hoboken"): "07030"})
    assert calculate("9 Elm St", "Hoboken", "", "blanks", r) == ("", "zip_not_worked_out")


def test_B06_a_blank_zip_with_a_resolvable_street_gets_the_nyc_zip():
    r = DictResolver({("209 Joralemon St", "Brooklyn"): "11201"})
    assert calculate("209 Joralemon St", "Brooklyn", "", "blanks", r) == ("11201", "zip_found")
