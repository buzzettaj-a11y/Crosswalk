"""C-22: the old logs echoed values in their messages. With every value a unique token, no token reaches either log, the
summary, the quality report or the receipt."""
from tests.support.files_run import run, write_csv
from tests.support.outputs import write
from wholecount.engine.outputs.receipt import receipt_text
from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
from wholecount.session import commands as C
from wholecount.session.export import build_view

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "Address_2", "City", "State", "Zip", "Program"]
ROWS = [["Zq1Id", "Zq1First", "Zq1Last", "1981-02-03", "11 Zq1Street St Apt 4D", "Apt 7F", "Brooklyn", "NY", "11201", "Zq1Prog"],
        ["Zq2Id", "Zq2First", "Zq2Last", "1982-03-04", "22 Zq2Street St", "", "Queens", "NY", "10451", "Zq1Prog"],
        ["Zq3Id", "Zq3First", "Zq3Last", "1983-04-05", "33 Zq3Street St", "", "Zq3City", "NY", "11222", "Zq1Prog"]]
TOKENS = ["Zq1Id", "Zq1First", "Zq1Last", "Zq1Street", "Apt 4D", "Apt 7F", "Zq2Id", "Zq2First", "Zq2Last", "Zq2Street",
          "Zq3Id", "Zq3First", "Zq3Last", "Zq3Street", "Zq3City", "1981-02-03", "1982-03-04", "1983-04-05", "11222"]


def test_no_token_anywhere_shared(tmp_path):
    s = run(tmp_path, [write_csv(tmp_path / "in" / "tokens.csv", COLS, ROWS)])
    keys = [k for k, o in s.results.outcomes.items() if o.reasons and o.set_aside_reason is None]
    s.history.execute(C.ApproveRows(keys, "*"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    receipt = write(s, tmp_path / "out")
    texts = {n: (tmp_path / "out" / n).read_text(encoding="utf-8-sig") for n in
             ("Internal_Audit_Log.txt", "Shareable_Audit_Log.txt", "Data_Quality_Report.csv")}
    texts["summary"] = render_summary_html(build_summary(build_view(s), True))
    texts["receipt"] = receipt_text(receipt)
    for name, text in texts.items():
        for t in TOKENS:
            assert t not in text, (name, t)
    assert "tokens.csv" not in texts["Shareable_Audit_Log.txt"]
