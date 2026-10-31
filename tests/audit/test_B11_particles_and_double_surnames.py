"""B-11 (High): particles, double surnames and compound given names were mis-split with no flag."""
import pytest

from wholecount.engine import reasons
from wholecount.engine.prepare.names import parse_name


@pytest.mark.parametrize("raw,first,middle,last", [
    ("Maria de la Cruz", "Maria", "", "de la Cruz"), ("Martin Van Buren", "Martin", "", "Van Buren"),
    ("Ludwig van Beethoven", "Ludwig", "", "van Beethoven"), ("Mohammed bin Salman", "Mohammed", "", "bin Salman"),
    ("Mary Jane Watson", "Mary Jane", "", "Watson"), ("Maria E Cruz", "Maria", "E", "Cruz"),
    ("de la Cruz, Maria", "Maria", "", "de la Cruz"), ("Cruz, Maria Elena", "Maria Elena", "", "Cruz"),
])
def test_B11_split_with_no_flag(raw, first, middle, last):
    n = parse_name(raw)
    assert (n.first, n.middle, n.last) == (first, middle, last) and n.notes == []


@pytest.mark.parametrize("raw,parts", [("Ana Garcia Lopez", ("Ana", "Garcia", "Lopez")), ("Kim Soo Jin", ("Kim", "Soo", "Jin"))])
def test_B11_three_words_keep_every_word_and_flag_soft(raw, parts):
    n = parse_name(raw)
    assert (n.first, n.middle, n.last) == parts and n.notes == ["name_order_unclear"]
    assert reasons.get("name_order_unclear").flag == "soft"
    import tomllib
    from importlib import resources
    problems = tomllib.loads(resources.files("wholecount.copy").joinpath("problems.toml").read_text(encoding="utf-8"))
    assert problems["name_order_unclear"]["title"] == "Name has three or more words: check which is the surname"
