"""P-READ-2: UTF-8 after removing a BOM, then Windows-1252, never with replacement characters."""
from tests.support.files import write_bytes, write_text
from wholecount.engine.read.reader import read_path


def test_bom_is_removed(tmp_path):
    rf = read_path(write_bytes(tmp_path, "a.csv", b"\xef\xbb\xbfName\nAna\n"))
    assert rf.grids[0].rows[0] == ["Name"] and rf.encoding == "utf-8"


def test_utf8_reads_as_utf8_with_no_samples(tmp_path):
    rf = read_path(write_text(tmp_path, "a.csv", "Name\nJosé\n"))
    assert rf.encoding == "utf-8" and rf.encoding_samples == [] and rf.grids[0].rows[1] == ["José"]


def test_samples_stop_at_five(tmp_path):
    names = ["José", "Zoë", "Peña", "Renée", "Núñez", "Müller", "Gómez"]
    rf = read_path(write_text(tmp_path, "a.csv", "Name\n" + "\n".join(names) + "\n", encoding="cp1252"))
    assert rf.encoding == "windows-1252"
    assert rf.encoding_samples == names[:5]


def test_a_literal_replacement_character_is_counted_and_left_in_the_cell(tmp_path):
    rf = read_path(write_text(tmp_path, "a.csv", "Name\nJos�\n"))
    assert rf.replacement_chars == 1 and rf.grids[0].rows[1] == ["Jos�"]
