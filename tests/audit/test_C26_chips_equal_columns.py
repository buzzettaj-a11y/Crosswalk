"""C-26: the old Download chips and the written columns disagreed. They read one list, and switching a column off changes no
count."""
import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.outputs import header, write
from wholecount.engine.outputs.columns import FileId, chip_columns
from wholecount.engine.outputs.view import ExportSettings
from wholecount.session.export import build_view


def test_every_file(tmp_path):
    s = session(tmp_path)
    settings = ExportSettings(map_points=True)
    write(s, tmp_path / "out", map_points=True)
    view = build_view(s, settings)
    for f in (FileId.FINAL_CLEAN_MAPPED, FileId.UNIQUE_CLIENTS, FileId.UNIQUE_CLIENTS_BY_PROGRAM, FileId.MANUAL_REVIEW_NEEDED,
              FileId.SET_ASIDE_RECORDS, FileId.MAP_COUNTS, FileId.MAP_POINTS, FileId.DATA_QUALITY_REPORT):
        assert header(tmp_path / "out" / f"{f.value}.csv") == chip_columns(f, view, settings), f


@pytest.mark.parametrize("column", ["Count_Status", "Date_of_Birth"])
def test_switching_off(tmp_path, column):
    s = session(tmp_path)
    counts = s.counts()
    write(s, tmp_path / "out", columns_off={FileId.FINAL_CLEAN_MAPPED: frozenset({column})})
    assert column not in header(tmp_path / "out" / "Final_Clean_Mapped.csv")
    assert s.counts() == counts
