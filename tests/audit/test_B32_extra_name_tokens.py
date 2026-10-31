"""B-32 (Medium): extra name words were dropped and the row stayed clean. Now every word is kept and the row is flagged."""
import pytest

from wholecount.engine import reasons
from wholecount.engine.prepare.names import parse_name


@pytest.mark.parametrize("raw,extra", [
    ("Smith, John Q Public", "Public"), ("Smith, John, Mary", "Mary"), ("John (Jack) Smith", "(Jack)"),
    ("John 'Johnny' Smith", "'Johnny'"),
])
def test_B32_leftovers_are_kept_and_flagged(raw, extra):
    n = parse_name(raw)
    assert n.extra == extra and n.first == "John" and n.last == "Smith"
    assert n.notes == ["name_extra_tokens"]
    assert reasons.get("name_extra_tokens").flag == "soft"
