"""A-02: the old audit log held cell values. Reasons appear as codes with record keys, and no value reaches either log."""
import csv

from tests.support.files_run import AUDIT_FIXTURES, run, write_csv
from tests.support.outputs import write
from wholecount.session import commands as C

BAD = ["Zebulon Quillfeather", "742 Evergreen Terrace", "Marigold Thistlewood", "Ignatius Wobblesworth", "ZORP", "Gotham", "Brookln"]


def test_logs_hold_codes_only(tmp_path):
    rows = list(csv.reader((AUDIT_FIXTURES / "misplaced.csv").open(encoding="utf-8")))
    header = rows[0] + ["DOB"]
    body = [r + [""] for r in rows[1:]] + [["M006", "Fay", "Ward", "60 Elm St", "Gotham", "NY", "11201", "Elder Care",
                                           "not-a-real-date-ZORP"], ["M007", "Gil", "Ross", "70 Elm St", "Brookln", "NY", "11201",
                                                                     "Elder Care", "1990-01-01"]]
    s = run(tmp_path, [write_csv(tmp_path / "in" / "misplaced.csv", header, body)])
    open_rows = [k for k, o in s.results.outcomes.items() if o.reasons and o.set_aside_reason is None]
    s.history.execute(C.ApproveRows(open_rows, "*"))
    s.history.execute(C.AcknowledgeLowConfidence()) if s.results.confidence.level == "low" else None
    write(s, tmp_path / "out")
    for log in ("Internal_Audit_Log.txt", "Shareable_Audit_Log.txt"):
        text = (tmp_path / "out" / log).read_text(encoding="utf-8")
        for v in BAD:
            assert v not in text, (log, v)
        assert "reason_code=" in text
    internal = (tmp_path / "out" / "Internal_Audit_Log.txt").read_text(encoding="utf-8")
    assert any(k in internal for k in open_rows)
