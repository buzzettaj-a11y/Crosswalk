"""A-03: the old summary and quality report held free text, IDs and people. Counts only, and file names only when ticked."""
import pytest

from tests.support.files_run import fixture, run
from tests.support.outputs import read, write
from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
from wholecount.session.export import build_view


def test_counts_only(tmp_path):
    s = run(tmp_path, fixture(tmp_path, "idconflict.csv", "household.csv"))
    write(s, tmp_path / "out")
    view = build_view(s)
    plain = render_summary_html(build_summary(view, False))
    named = render_summary_html(build_summary(view, True))
    report = (tmp_path / "out" / "Data_Quality_Report.csv").read_text(encoding="utf-8-sig")
    for text in (plain, named, report):
        for v in ("SSN-123-45-6789", "Snodgrass", "Grumblethorpe", "H100", "Ballpeen", "M-"):
            assert v not in text, v
    assert {r["Source_File"] for r in read(tmp_path / "out" / "Data_Quality_Report.csv")} == {"idconflict.csv", "household.csv"}
    for name in ("idconflict", "household"):
        assert name not in plain
        assert name in named
    assert "Counts only." in plain and "Counts and file names only." in named
