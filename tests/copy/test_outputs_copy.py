"""H11: a corrected row and a filled row say exactly what happened to them, and never that they passed every check."""
import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.outputs import read, write
from tests.support.session import rk
from wholecount.engine.corrections import VerifiedCorrection
from wholecount.session import commands as C


@pytest.mark.claim("CL-OUT-01")
@pytest.mark.claim("CL-OUT-02")
def test_corrected_and_filled_rows(tmp_path):
    s = session(tmp_path)
    s.history.execute(C.AcceptFills([rk(s, "R13")]))
    s.history.execute(C.ApplyCorrections([VerifiedCorrection(rk(s, "R14"), (("First_Name", "Mo"),))], "f" * 64, "c.csv"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    write(s, tmp_path / "out")
    rows = {r["Record_Key"]: r for r in read(tmp_path / "out" / "Final_Clean_Mapped.csv")}
    assert rows[rk(s, "R14")]["Count_Status"] == "Counted, corrected from a corrections file"
    assert rows[rk(s, "R13")]["Location_Status"] == "Filled from the row's own address"
    assert not any("passed every check" in r["Count_Status"] or "passed every check" in r["Location_Status"] for r in rows.values())
