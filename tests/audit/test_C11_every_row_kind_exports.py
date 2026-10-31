"""C-11: the old export crashed on some row kinds and listed summary rows for review. Every kind writes, and a summary row is
set aside, never in the review file (P-VAL-3). The audit expected it in the review file; the spec sets it aside."""
from tests.support.files_run import run, write_csv
from tests.support.outputs import read, write
from wholecount.engine.corrections import VerifiedCorrection
from wholecount.session import commands as C

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
ROWS = [["K1", "Ann", "North", "1980-01-01", "1 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["K2", "", "South", "1981-01-01", "2 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["K3", "Cal", "East", "1982-01-01", "3 Oak St", "Queens", "NY", "10451", "Housing"],
        ["K4", "Dee", "West", "1983-01-01", "4 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["K4", "Dee", "West", "1983-01-01", "4 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["K6", "Eve", "Low", "1984-01-01", "6 Oak St", "Brooklyn", "NY", "", "Housing"],
        ["", "Total", "", "", "", "", "", "", ""]]


def test_every_kind(tmp_path):
    s = run(tmp_path, [write_csv(tmp_path / "in" / "k.csv", COLS, ROWS)])
    g = next(g for g in s.results.groups if g.kind == "identical")
    s.history.execute(C.KeepOneInCopyGroup(g.group_id, g.members[0]))
    k6 = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "K6")
    s.history.execute(C.ApplyCorrections([VerifiedCorrection(k6, (("Zip", "11201"),))], "f" * 64, "c.csv"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    for fmt in ("csv", "xlsx", "json"):
        out = tmp_path / fmt
        write(s, out, formats={n: fmt for n in ("Final_Clean_Mapped", "Unique_Clients", "Unique_Clients_By_Program",
                                                 "Manual_Review_Needed", "Set_Aside_Records", "Map_Counts")})
    review = {r["Client_ID"]: r for r in read(tmp_path / "csv" / "Manual_Review_Needed.csv")}
    assert set(review) == {"K2", "K3"}
    assert review["K2"]["Original_First_Name"] == "" and review["K3"]["Original_City"] == "Queens"
    aside = read(tmp_path / "csv" / "Set_Aside_Records.csv")
    assert sorted(r["Reason"] for r in aside) == ["Copy of another row", "Summary row"]
