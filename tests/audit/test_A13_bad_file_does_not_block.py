"""A-13 (Medium): a bad file in a multi-file upload returned an error and dropped the files after it."""
from tests.support.files import write_bytes, write_text, write_xlsx
from tests.support.load import load


def test_A13_bad_files_do_not_block_good_ones(tmp_path):
    good1 = write_text(tmp_path, "good1.csv", "Client_ID,First_Name,Last_Name\n1,Ana,Lee\n")
    docx = write_bytes(tmp_path, "renamed.docx", b"PK\x03\x04 a word file")
    xl = write_xlsx(tmp_path, "trunc.xlsx", {"S": [["A"], ["1"]]})
    xl.write_bytes(xl.read_bytes()[:200])
    bad = write_bytes(tmp_path, "bad.csv", b"A,B\n\x81,1\n")
    good2 = write_text(tmp_path, "good2.csv", "Client_ID,First_Name,Last_Name\n2,Ben,Cho\n")
    r = load([good1, docx, xl, bad, good2])
    assert [(f.name, f.status, f.reason_id, f.letter) for f in r.files] == [
        ("good1.csv", "ok", None, "A"), ("renamed.docx", "unreadable", "unsupported_type", None),
        ("trunc.xlsx", "unreadable", "bad_workbook", None), ("bad.csv", "unreadable", "unreadable_encoding", None),
        ("good2.csv", "ok", None, "B"),
    ]
    assert [t.letter for t in r.tables] == ["A", "B"]
    assert r.counts() == {"ok": 2, "unreadable": 3, "duplicate_file": 0}


def test_A13_same_file_twice_is_skipped_as_a_duplicate(tmp_path):
    a = write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name\n1,Ana,Lee\n")
    d = tmp_path / "sub"
    d.mkdir()
    b = write_text(d, "a.csv", "Client_ID,First_Name,Last_Name\n1,Ana,Lee\n")
    r = load([a, b])
    assert [f.status for f in r.files] == ["ok", "duplicate_file"] and len(r.tables) == 1
