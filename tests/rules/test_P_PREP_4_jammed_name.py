"""P-PREP-4: the jammed-name rules beyond the audit cases."""
import pytest

from wholecount.engine.prepare.names import parse_name


@pytest.mark.parametrize("raw,first,middle,last,suffix", [
    ("Smith Jr, John", "John", "", "Smith", "Jr"), ("Smith, John A", "John", "A", "Smith", ""), ("John A Smith", "John", "A", "Smith", ""),
    ("DiNapoli, Anthony", "Anthony", "", "DiNapoli", ""), ("MARIA GARCIA", "MARIA", "", "GARCIA", ""), ("Martin V Buren", "Martin", "V", "Buren", ""),
    ("Fontaine,", "", "", "Fontaine", ""), ("Smith-Jones, Ann", "Ann", "", "Smith-Jones", ""), ("Garcia Lopez, Ana", "Ana", "", "Garcia Lopez", ""),
])
def test_cases(raw, first, middle, last, suffix):
    n = parse_name(raw)
    assert (n.first, n.middle, n.last, n.suffix) == (first, middle, last, suffix)


def test_last_first_form():
    n = parse_name("Lee Ana", form="last_first")
    assert (n.first, n.last) == ("Ana", "Lee")


def test_sr_at_the_start_needs_two_words_after_it():
    assert parse_name("Sr. Maria Lopez").title == "Sr."
    n = parse_name("Sr Lopez")
    assert n.title == "" and n.last == "Lopez"
