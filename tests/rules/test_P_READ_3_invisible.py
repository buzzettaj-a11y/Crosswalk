"""P-READ-3: invisible characters are removed and counted, and spacing collapses."""
import pytest

from tests.support.files import write_text
from wholecount.engine.read.clean import clean_cell
from wholecount.engine.read.reader import read_path


@pytest.mark.parametrize("raw,group", [
    ("Ana​", "zero_width"), ("Ana‌", "zero_width"), ("Ana‍", "zero_width"), ("Ana⁠", "zero_width"),
    ("﻿Ana", "bom"), ("An­a", "soft_hyphen"), ("Ana\x00", "control"), ("A\x07na", "control"), ("Ana\x7f", "control"),
])
def test_each_group_is_removed_and_counted(raw, group):
    text, counts = clean_cell(raw)
    assert text == "Ana"
    assert counts.as_dict()[group] == 1 and counts.total() == 1


@pytest.mark.parametrize("raw", ["Ana\tLee", "Ana\rLee", "Ana\nLee", "Ana Lee", "Ana Lee", "Ana   Lee", " Ana \t Lee "])
def test_spaces_collapse_to_one(raw):
    assert clean_cell(raw)[0] == "Ana Lee"


def test_controls_do_not_become_spaces():
    assert clean_cell("An\x00a")[0] == "Ana"


def test_case_digits_and_punctuation_are_untouched():
    assert clean_cell("O'BRIEN-smith, 07030.")[0] == "O'BRIEN-smith, 07030."


def test_one_leading_apostrophe_is_removed_when_something_follows():
    assert clean_cell("'07030") == ("07030", clean_cell("'07030")[1])
    assert clean_cell("'07030")[1].apostrophe == 1
    assert clean_cell("''x")[0] == "'x"
    assert clean_cell("'")[0] == "'"


def test_file_counts_sum_over_cells(tmp_path):
    rf = read_path(write_text(tmp_path, "a.csv", "Name,Zip\nAna​,'07030\n​Ben,10001\n"))
    assert rf.clean_counts["zero_width"] == 2 and rf.clean_counts["apostrophe"] == 1
