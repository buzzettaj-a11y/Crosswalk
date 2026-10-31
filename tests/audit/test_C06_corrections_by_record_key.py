"""C-06: the old corrections were addressed by row position, so a sorted or extended file corrected the wrong row."""
import csv

from tests.fixtures.session import r_fixture
from wholecount.engine.corrections import VerifiedCorrection
from wholecount.engine.standardize.model import CountStatus
from wholecount.session import commands as C
from wholecount.session.runner import process

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
ROWS = [["A100", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["A200", "Ben", "Cruz", "1981-02-02", "12 Oak St", "Brooklyn", "NY", "11201", "Housing"],
        ["A300", "Cara", "Diaz", "1982-03-03", "14 Oak St", "Brooklyn", "NY", "11201", "Youth"],
        ["A400", "Dev", "Rao", "1983-04-04", "16 Oak St", "Brooklyn", "NY", "11201", "Youth"],
        ["A500", "", "Fox", "1984-05-05", "18 Oak St", "Brooklyn", "NY", "11201", "Youth"],
        ["A900", "Zed", "Zimmer", "1990-01-01", "22 Oak St", "Brooklyn", "NY", "", "Housing"]]


def run(tmp_path, rows):
    path = tmp_path / "A.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    s = r_fixture.session(tmp_path, paths=[path])
    process(s)
    return s


def key(s, cid):
    return next(k for k, r in s.results.rows.items() if r.value("Client_ID") == cid)


def fix(s, cid="A900", field="Zip", text="11201"):
    cmd = C.ApplyCorrections([VerifiedCorrection(key(s, cid), ((field, text),))], "f" * 64, "review.xlsx")
    s.history.execute(cmd)
    return cmd


def test_sorted_source_only_a900_changes(tmp_path):
    s = run(tmp_path / "plain", ROWS)
    fix(s)
    want = s.counts()
    s2 = run(tmp_path / "sorted", sorted(ROWS, key=lambda r: r[2]))
    before = dict(s2.results.outcomes)
    fix(s2)
    changed = [k for k, o in s2.results.outcomes.items() if o != before[k]]
    assert changed == [key(s2, "A900")]
    assert s2.results.outcomes[key(s2, "A900")].count_status == CountStatus.COUNTED_CORRECTED
    assert s2.counts() == want


def test_new_client_at_the_top(tmp_path):
    s = run(tmp_path, [["A050", "New", "Person", "1999-09-09", "40 Oak St", "Brooklyn", "NY", "11201", "Youth"]] + ROWS)
    fix(s)
    assert s.results.outcomes[key(s, "A900")].count_status == CountStatus.COUNTED_CORRECTED
    assert s.results.rows[key(s, "A900")].value("Zip") == "11201"


def test_refusals(tmp_path):
    s = run(tmp_path, ROWS)
    k = key(s, "A900")
    s.history.execute(C.SetAsideRows([key(s, "A100")], "test_record"))
    cmd = C.ApplyCorrections([VerifiedCorrection(k, (("Zip", "11201"),)), VerifiedCorrection(k, (("Zip", "11202"),)),
                              VerifiedCorrection("0" * 20, (("Zip", "11201"),)),
                              VerifiedCorrection(key(s, "A100"), (("Zip", "10001"),))], "f" * 64)
    s.history.execute(cmd)
    assert sorted(cmd.report.refused) == sorted([("duplicate_in_file", k), ("unknown_record", "0" * 20),
                                                ("row_set_aside", key(s, "A100"))])


def test_still_failing_stays_not_counted(tmp_path):
    s = run(tmp_path, ROWS)
    fix(s, "A500", "Zip", "11222")
    assert s.results.outcomes[key(s, "A500")].count_status == CountStatus.NOT_COUNTED_YET


def test_no_value_in_the_audit(tmp_path):
    s = run(tmp_path, ROWS)
    fix(s)
    text = repr(s.audit)
    for v in ("11201", "Zimmer", "Zed", "22 Oak St"):
        assert v not in text
    e = s.audit[-1]
    assert e.code == "CORRECTION" and e.get("old_hash") and e.get("new_hash") and e.get("field_name") == ["Zip"]
