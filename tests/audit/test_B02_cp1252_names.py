"""B-02 (High): a Windows-1252 CSV was decoded with replacement characters and the rows stayed clean.
Now it is read as Windows-1252 exactly, with sample values for the callout, and bytes neither encoding defines are refused."""
import pytest

from tests.support.files import write_bytes, write_text
from wholecount.engine.read.model import UnreadableFile
from wholecount.engine.read.reader import read_path

NAMES = ["José Núñez", "Zoë Müller", "Ana Peña", "Renée O'Brien"]

pytestmark = pytest.mark.claim("CL-READ-ENCODING-01")


def cp1252_file(tmp_path):
    return write_text(tmp_path, "names.csv", "Name\n" + "\n".join(NAMES) + "\n", encoding="cp1252")


def test_B02_cp1252_names_read_back_exactly(tmp_path):
    rf = read_path(cp1252_file(tmp_path))
    assert [r[0] for r in rf.grids[0].rows[1:]] == NAMES
    assert rf.encoding == "windows-1252"
    assert len(rf.encoding_samples) <= 5 and "José Núñez" in rf.encoding_samples


def test_B02_undecodable_bytes_rejected(tmp_path):
    with pytest.raises(UnreadableFile) as e:
        read_path(write_bytes(tmp_path, "bad.csv", b"A,B\n\x81,\x8d\n"))
    assert e.value.reason_id == "unreadable_encoding"


def test_B02_no_replacement_character_in_any_cell(tmp_path):
    rf = read_path(cp1252_file(tmp_path))
    assert rf.replacement_chars == 0
    assert not any("�" in c for g in rf.grids for r in g.rows for c in r)
