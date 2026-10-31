"""A-10: the old review screen let a reviewer type a value. Values come back only through a signed corrections file, and only
for fields that failed."""
import inspect

from tests.support.files_run import fixture, run
from tests.support.outputs import read, write
from tests.support.review import cell, read_back, review_grid
from wholecount.session import commands as C

FREE_TEXT = {"value", "text", "values", "new_text"}


def test_no_command_takes_a_value():
    for cmd in C.ALL_COMMANDS:
        params = set(inspect.signature(cmd.__init__).parameters) - {"self"}
        assert not params & FREE_TEXT, cmd.__name__


def test_zip_applies_and_the_name_edit_is_refused(tmp_path):
    s = run(tmp_path, fixture(tmp_path, "household.csv"))
    zed = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "H300")
    grid = review_grid(s, tmp_path / "out")
    cell(grid, zed, "Corrected_Zip", "11201")
    cell(grid, zed, "Last_Name", "Somebodyelse")
    got = read_back(s, grid, tmp_path / "corrections.csv")
    assert [(x.code, x.column) for x in got.refused] == [("other_column_changed", "Last_Name")]
    s.history.execute(C.ApplyCorrections(got.accepted, got.fingerprint, got.file_name))
    s.history.execute(C.AcknowledgeLowConfidence()) if s.results.confidence.level == "low" else None
    write(s, tmp_path / "out2")
    clean = {r["Record_Key"]: r for r in read(tmp_path / "out2" / "Final_Clean_Mapped.csv")}
    assert clean[zed]["Count_Status"] == "Counted, corrected from a corrections file" and clean[zed]["Last_Name"] == "Nobody"
    internal = (tmp_path / "out2" / "Internal_Audit_Log.txt").read_text(encoding="utf-8")
    line = next(l for l in internal.splitlines() if " CORRECTION " in l)
    assert zed in line and 'field_name="Zip"' in line and "old_hash=" in line and 'file_name="corrections.csv"' in line
    share = (tmp_path / "out2" / "Shareable_Audit_Log.txt").read_text(encoding="utf-8")
    for text in (internal, share):
        for v in ("Nobody", "Somebodyelse", "11201"):
            assert v not in text, v
    assert "corrections.csv" not in share
