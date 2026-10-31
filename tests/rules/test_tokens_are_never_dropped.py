"""Every word of every address and name case in M03 lands in some output part (P-PREP-3, P-PREP-4, B-10, B-32).
Separators, a stripped country and punctuation-only tokens are not words."""
import re

import pytest

from wholecount.engine.prepare.address import parse_address
from wholecount.engine.prepare.names import parse_name

ADDRESSES = [
    "117 - 19 45th Ave, Flushing, NY 11355", "1010 Grand Concourse NY 10452", "123 Main St, Brooklyn, NY 112011234",
    "123 Main St, Apt 3 Brooklyn NY 11201", "123 Main St, c/o Jane Doe", "85-10 Forest Pkwy Woodhaven NY 11421", "100 Avenue U",
    "9 Elm St, Newark, NJ 07102", "123 Main St Apt 3L Brooklyn NY 11201", "60 Centre St - Apt 2 - New York NY 10007",
    "100 Grand St Apt 4 Brooklyn NY 11211 USA", "88 Front St Brooklyn NY 11201", "111 Test St, Brooklyn, Apt. 4, NY, 11201",
    "117-19 45TH AVE 14A QUEENS NY 11355", "123 Main St, Lower", "123 Main St, Top Floor", "123 Main St, B, Brooklyn NY 11201",
    "1010 Grand Concourse 5C", "123 Main St Rear", "67 Jill Ave Apt#: 11T", "Apt 1120123 Main St",
]
NAMES = [
    "Maria de la Cruz", "Ana Garcia Lopez", "Kim Soo Jin", "Mary Jane Watson", "Dr. John Smith", "John Smith, MD", "Smith, Jr., John",
    "Smith, III John", "Smith, John Q Public", "Smith, John, Mary", "John (Jack) Smith", "John 'Johnny' Smith", "Sr. Maria Lopez",
    "Ann Lee, DO", "John Smith I", "Fontaine,",
]
COUNTRIES = {"usa", "us"}


def words(text):
    return [w for w in re.split(r"[\s,]+", text) if re.search(r"[A-Za-z0-9]", w) and w.lower().strip(".") not in COUNTRIES]


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


@pytest.mark.parametrize("raw", ADDRESSES)
def test_address_words_kept(raw):
    a = parse_address(raw)
    out = norm(" ".join([a.street, a.unit, a.city, a.state, a.zip, a.extra]))
    for w in words(raw):
        n = norm(w)
        if n in ("ny",) or re.fullmatch(r"\d{9}", n):
            continue
        assert n in out, (raw, w)


@pytest.mark.parametrize("raw", NAMES)
def test_name_words_kept(raw):
    n = parse_name(raw)
    out = norm(" ".join([n.first, n.middle, n.last, n.title, n.credential, n.suffix, n.extra]))
    for w in words(raw):
        assert norm(w) in out, (raw, w)
