"""The five example files with the planned decisions, with the practice reference and with no backend: every file's row count
equals the outputs section of EXPECTED.json, and the counts equal its after_decisions section."""
import pytest

from tests.support.example_session import PLAN, decide, example_session
from tests.support.outputs import read, write


@pytest.mark.parametrize("practice", [True, False])
def test_row_counts(tmp_path, practice):
    s = decide(example_session(tmp_path, practice))
    receipt = write(s, tmp_path / "out")
    want = PLAN["outputs"]["practice_run" if practice else "no_geocoder_run"]
    pre = "PRACTICE_" if practice else ""
    rows = {f.path.rsplit("/", 1)[-1].replace(pre, "").rsplit(".", 1)[0]: f.rows for f in receipt.files}
    for name in ("Final_Clean_Mapped", "Set_Aside_Records", "Manual_Review_Needed", "Unique_Clients", "Unique_Clients_By_Program",
                 "Data_Quality_Report"):
        assert rows[name] == want[name], name
    review = read(tmp_path / "out" / f"{pre}Manual_Review_Needed.csv")
    assert sum(r["Counted"] == "No" for r in review) == want["Manual_Review_Needed_counted_no"]
    after = PLAN["counts"]["after_decisions"]
    c = s.counts()
    assert (c.counted, c.not_counted_yet, c.set_aside, c.goal1.high, c.goal2.high) == (
        after["counted"], after["not_counted_yet"], after["set_aside"], after["goal_1"]["high"], after["goal_2"]["high"])
    assert {p: r.high for p, r in c.per_program.items()} == after["per_program"]
