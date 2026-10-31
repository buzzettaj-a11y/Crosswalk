"""B-24 (Medium): zero-width characters, BOMs, soft hyphens, NUL and a leading apostrophe survived cleaning."""
from wholecount.engine.read.clean import clean_cell


def text(s):
    return clean_cell(s)[0]


def test_B24_invisible_characters_removed():
    assert text("Ana​") == "Ana"
    assert text("﻿Ana") == "Ana"
    assert text("An­a") == "Ana"
    assert text("Ana\x00") == "Ana"
    assert text("A1​") == text("A1")


def test_B24_leading_apostrophe_removed():
    assert text("'07030") == "07030"
    assert text("'Ana") == "Ana"
    assert text("'0012345") == "0012345"


def test_B24_counts_per_group():
    _, c = clean_cell("﻿'A​n­a\x00‌")
    assert c.as_dict() == {"zero_width": 2, "bom": 1, "soft_hyphen": 1, "control": 1, "apostrophe": 1}


def test_B24_nbsp_only_cell_is_empty():
    assert text(" ") == "" and text("   ") == ""
