"""Source letters (SPEC 4.3)."""
import pytest

from wholecount.engine.letters import letter_for_index


@pytest.mark.parametrize("i,letter", [(0, "A"), (25, "Z"), (26, "AA"), (51, "AZ"), (52, "BA"), (701, "ZZ"), (702, "AAA")])
def test_letters(i, letter):
    assert letter_for_index(i) == letter


def test_negative_index_raises():
    with pytest.raises(ValueError):
        letter_for_index(-1)
