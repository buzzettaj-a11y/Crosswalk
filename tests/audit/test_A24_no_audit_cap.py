"""A-24: the old audit stopped at 2,000 decision lines. Every decision gets its line."""
from tests.support.files_run import run, write_csv
from tests.support.outputs import write
from wholecount.session import commands as C

N = 2100


def test_2100_lines(tmp_path):
    rows = [[f"C{i:05d}", f"Given{i}", f"Family{i}", f"{1 + i % 900} Oak St", "Brooklyn", "NY", "", "Housing"] for i in range(N)]
    path = write_csv(tmp_path / "in" / "big.csv", ["Client_ID", "First_Name", "Last_Name", "Address_1", "City", "State", "Zip",
                                                   "Program"], rows)
    s = run(tmp_path, [path])
    keys = [k for k, o in s.results.outcomes.items() if "address_part_missing" in o.reasons]
    assert len(keys) == N
    s.history.execute(C.ApproveRows(keys, "address_part_missing", second="Sam"))
    s.history.execute(C.AcknowledgeLowConfidence()) if s.results.confidence.level == "low" else None
    write(s, tmp_path / "out")
    for log in ("Internal_Audit_Log.txt", "Shareable_Audit_Log.txt"):
        lines = [l for l in (tmp_path / "out" / log).read_text(encoding="utf-8").splitlines() if " DECISION " in l]
        assert len(lines) == N and len({l.split("record_key=")[1].split()[0] for l in lines}) == N
        assert not any("more" in l for l in lines)
