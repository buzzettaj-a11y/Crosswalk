"""P-READ-8: a file that can't be read gives a reason ID, never text from the file."""
import pytest

from tests.support.files import write_bytes, write_text, write_xlsx
from wholecount.engine.read.model import UnreadableFile
from wholecount.engine.read.reader import read_path


def reason(path):
    with pytest.raises(UnreadableFile) as e:
        read_path(path)
    return e.value.reason_id


def test_reasons(tmp_path):
    assert reason(write_bytes(tmp_path, "a.docx", b"PK\x03\x04 not a doc")) == "unsupported_type"
    assert reason(write_bytes(tmp_path, "a.csv", b"A,B\n\x81,\x8d\n")) == "unreadable_encoding"
    assert reason(write_bytes(tmp_path, "a.xlsx", b"PK\x03\x04 truncated")) == "bad_workbook"
    assert reason(write_text(tmp_path, "a.json", "{not json")) == "bad_json"
    assert reason(write_text(tmp_path, "a.xml", "<a><b></a>")) == "bad_xml"
    assert reason(write_bytes(tmp_path, "e.csv", b"")) == "empty_file"
    assert reason(write_bytes(tmp_path, "f.csv", b"  \n \r\n")) == "empty_file"


def test_truncated_real_workbook(tmp_path):
    p = write_xlsx(tmp_path, "a.xlsx", {"S": [["A"], ["1"]]})
    data = p.read_bytes()
    p.write_bytes(data[: len(data) // 2])
    assert reason(p) == "bad_workbook"


def test_reason_carries_no_file_text(tmp_path):
    p = write_bytes(tmp_path, "a.csv", "Name\nSECRET-VALUE-\x81\n".encode("latin-1"))
    with pytest.raises(UnreadableFile) as e:
        read_path(p)
    assert "SECRET" not in str(e.value) and "SECRET" not in repr(e.value)
