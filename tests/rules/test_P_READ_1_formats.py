"""P-READ-1: six formats, every value read as text, and .xlsx number formats kept beside the text."""
import datetime as dt

import pytest

from tests.support.files import write_text, write_xlsx
from wholecount.engine.read.model import CellMeta
from wholecount.engine.read.reader import read_path
from wholecount.engine.read.xlsx import cell_text


def only_grid(rf):
    assert len(rf.grids) == 1
    return rf.grids[0]


def test_csv_keeps_leading_zeros(tmp_path):
    g = only_grid(read_path(write_text(tmp_path, "a.csv", "Zip,Name\n07030,Ana\n00501,Ben\n")))
    assert g.rows == [["Zip", "Name"], ["07030", "Ana"], ["00501", "Ben"]]


def test_tsv_and_txt(tmp_path):
    assert only_grid(read_path(write_text(tmp_path, "a.tsv", "A\tB\n1\t2\n"))).rows == [["A", "B"], ["1", "2"]]
    assert only_grid(read_path(write_text(tmp_path, "a.txt", "A|B|C\n1|2|3\n4|5|6\n"))).rows[1] == ["1", "2", "3"]
    assert only_grid(read_path(write_text(tmp_path, "b.txt", "A;B\n1;2\n"))).rows[1] == ["1", "2"]


def test_txt_delimiter_ties_go_to_comma_first(tmp_path):
    assert only_grid(read_path(write_text(tmp_path, "a.txt", "A,B;C\n1,2;3\n"))).rows[0] == ["A", "B;C"]


def test_csv_row_numbers_follow_records_and_quoted_newlines_stay_in_one_cell(tmp_path):
    g = only_grid(read_path(write_text(tmp_path, "a.csv", 'A,B\n"x\ny",2\n3,4\n')))
    assert g.rows == [["A", "B"], ["x y", "2"], ["3", "4"]]


def test_xlsx_zip_format_date_and_general_number(tmp_path):
    p = write_xlsx(tmp_path, "a.xlsx", {"Clients": [
        ["Zip", "Born", "Serial"],
        [(7030, "00000"), (dt.date(1990, 4, 3), "yyyy-mm-dd"), 32874],
    ]})
    g = only_grid(read_path(p))
    assert g.rows[1] == ["07030", "1990-04-03", "32874"]
    assert g.meta[(1, 0)] == CellMeta("number", "00000")
    assert g.meta[(1, 1)].kind == "date"
    assert g.meta[(1, 2)] == CellMeta("number", "General")
    assert (0, 0) not in g.meta


def test_xlsx_reads_every_sheet_and_marks_hidden(tmp_path):
    p = write_xlsx(tmp_path, "a.xlsx", {"One": [["A"], ["1"]], "~Two": [["B"], ["2"]]})
    rf = read_path(p)
    assert [(g.sheet, g.hidden) for g in rf.grids] == [("One", False), ("Two", True)]


@pytest.mark.parametrize("value,fmt,text", [
    (None, "General", ""), (True, "General", "TRUE"), (False, "General", "FALSE"), (5, "General", "5"), (5.0, "General", "5"),
    (7030, "00000", "07030"), (12.5, "General", "12.5"), (12.5, "0.00", "12.50"), (0.1, "General", "0.1"),
    (dt.datetime(2024, 3, 15), "yyyy-mm-dd", "2024-03-15"), (dt.datetime(2024, 3, 15, 9, 5, 7), "General", "2024-03-15 09:05:07"),
    (dt.date(2024, 3, 15), "General", "2024-03-15"), (dt.time(9, 5, 7), "h:mm:ss", "09:05:07"), ("Ana", "General", "Ana"),
])
def test_cell_text(value, fmt, text):
    assert cell_text(value, fmt) == text


def test_json_numbers_stay_as_typed_and_nesting_flattens(tmp_path):
    p = write_text(tmp_path, "a.json",
                   '{"export": {"clients": [{"id": 007, "zip": "07030", "amount": 1.50, "active": true, "note": null,'
                   ' "address": {"city": "Bronx"}, "tags": ["a", "b"]}]}}'.replace("007", '"007"'))
    g = only_grid(read_path(p))
    assert g.fixed_header == ["id", "zip", "amount", "active", "note", "address.city", "tags"]
    assert g.rows == [["007", "07030", "1.50", "true", "", "Bronx", "a; b"]]


def test_json_top_level_list_and_single_object(tmp_path):
    g = only_grid(read_path(write_text(tmp_path, "a.json", '[{"a": 1}, {"b": 2.0}]')))
    assert g.fixed_header == ["a", "b"] and g.rows == [["1", ""], ["", "2.0"]]
    g = only_grid(read_path(write_text(tmp_path, "b.json", '{"a": 1, "b": "x"}')))
    assert g.rows == [["1", "x"]]


def test_xml_records_attributes_and_nesting(tmp_path):
    p = write_text(tmp_path, "a.xml", '<clients><client id="7"><name>Ana</name><address><zip>07030</zip></address></client>'
                                      '<client id="8"><name>Ben</name></client></clients>')
    g = only_grid(read_path(p))
    assert g.fixed_header == ["@id", "name", "address.zip"]
    assert g.rows == [["7", "Ana", "07030"], ["8", "Ben", ""]]
