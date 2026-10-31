"""B-12 (High): titles and suffixes became first or last names. They now go to their own parts and never become a name."""
import pytest

from wholecount.engine.prepare.names import parse_name


@pytest.mark.parametrize("raw,first,last,title,credential,suffix", [
    ("Dr. John Smith", "John", "Smith", "Dr.", "", ""), ("Mr John Smith", "John", "Smith", "Mr", "", ""),
    ("Mrs. Jane Doe", "Jane", "Doe", "Mrs.", "", ""), ("Rev. John Smith", "John", "Smith", "Rev.", "", ""),
    ("John Smith, MD", "John", "Smith", "", "MD", ""), ("John Smith PhD", "John", "Smith", "", "PhD", ""),
    ("John Smith V", "John", "Smith", "", "", "V"), ("John Smith VI", "John", "Smith", "", "", "VI"),
    ("John Smith 2nd", "John", "Smith", "", "", "2nd"), ("John Smith 3rd", "John", "Smith", "", "", "3rd"),
    ("Smith, Jr., John", "John", "Smith", "", "", "Jr."), ("Smith, III John", "John", "Smith", "", "", "III"),
])
def test_B12_the_twelve_audit_inputs(raw, first, last, title, credential, suffix):
    n = parse_name(raw)
    assert (n.first, n.last, n.title, n.credential, n.suffix) == (first, last, title, credential, suffix)


@pytest.mark.parametrize("raw,field,value", [
    ("Mx Alex Rivera", "title", "Mx"), ("Fr. Tom Brown", "title", "Fr."), ("Sr. Maria Lopez", "title", "Sr."),
    ("John Smith Sr", "suffix", "Sr"), ("Ann Lee, DO", "credential", "DO"), ("Jo Park EdD", "credential", "EdD"),
    ("Sam Fox LPN", "credential", "LPN"), ("Pat Ray NP", "credential", "NP"), ("Lee Cho LMSW", "credential", "LMSW"),
    ("John Smith I", "suffix", "I"),
])
def test_B12_position_rules(raw, field, value):
    n = parse_name(raw)
    assert getattr(n, field) == value
    assert value not in (n.first, n.middle, n.last)


def test_B12_anh_do_and_a_comma_initial():
    n = parse_name("Anh Do")
    assert (n.first, n.last, n.credential) == ("Anh", "Do", "")
    n = parse_name("Smith, John I")
    assert (n.first, n.middle, n.last, n.suffix) == ("John", "I", "Smith", "")
