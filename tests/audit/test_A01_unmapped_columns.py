"""A-01: the old review file copied every source column, SSNs included. Unmapped columns never leave the tool (H10)."""
import pytest

from tests.support.files_run import fixture, run
from tests.support.outputs import all_bytes, header, read, write
from wholecount.engine.outputs.receipt import receipt_text
from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
from wholecount.session.export import build_view

SECRETS = ["078-05-1120", "219-09-9999", "457-55-5462", "555-0101", "555-0102", "555-0103"]


@pytest.mark.parametrize("keep", [frozenset(), frozenset({"SSN"})])
def test_nothing_leaves(tmp_path, keep):
    s = run(tmp_path, fixture(tmp_path, "ssn_unmapped.csv"), keep_sensitive=keep)
    out = tmp_path / "out"
    receipt = write(s, out, formats={"Final_Clean_Mapped": "xlsx", "Unique_Clients": "json"})
    (out / "summary.html").write_text(render_summary_html(build_summary(build_view(s), True)))
    (out / "receipt.txt").write_text(receipt_text(receipt))
    for name, text in all_bytes(out).items():
        for v in SECRETS:
            assert v not in text, (name, v)
    review = read(out / "Manual_Review_Needed.csv")
    assert [r["Client_ID"] for r in review] == ["S002"] and review[0]["Original_Zip"] == ""
    assert "SSN" not in header(out / "Manual_Review_Needed.csv") and "Phone" not in header(out / "Final_Clean_Mapped.xlsx")
