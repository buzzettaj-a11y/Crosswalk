"""P-DUP-6 folding."""
import pytest

from wholecount.engine.fold import fold


@pytest.mark.parametrize("a,b", [
    ("José", "Jose"), ("O'Brien", "OBrien"), ("Mary-Ann", "MaryAnn"), ("VAN BUREN", "van buren"), ("Jose\u0301", "Jose"),
    ("Núñez", "nunez"),
])
def test_fold_equal(a, b):
    assert fold(a) == fold(b)


def test_fold_keeps_letters_and_digits_only():
    assert fold(" Ana-Lee 2nd! ") == "analee2nd"
