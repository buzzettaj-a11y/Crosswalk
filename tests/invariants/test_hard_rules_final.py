"""The hard rules at the end of the rewrite (SPEC 13.2, M15): all sixteen rows are done, each with at least one test that
exists and is collected."""
from tests.conftest import ROOT
from tests.invariants.test_hard_rules_map import parse_rows
from tests.support.collect import collected


def final_problems(rows, root, collected_files):
    found = [f"H{n}: no row" for n in range(1, 17) if f"H{n}" not in rows]
    for rule, row in sorted(rows.items()):
        if row["status"] != "done":
            found.append(f"{rule}: {row['status']}")
        if not row["tests"]:
            found.append(f"{rule}: no test")
        for t in row["tests"]:
            if not (root / t).is_file():
                found.append(f"{rule}: missing {t}")
            elif t not in collected_files:
                found.append(f"{rule}: {t} isn't collected")
    return found


def test_sixteen_rules_done_and_collected():
    rows = parse_rows((ROOT / "tests" / "HARD_RULES.md").read_text(encoding="utf-8"))
    assert len(rows) == 16
    files = {t for r in rows.values() for t in r["tests"]}
    assert final_problems(rows, ROOT, collected(files)) == []


def test_negative_controls_on_a_copy(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text("def test_x():\n    pass\n")
    text = (ROOT / "tests" / "HARD_RULES.md").read_text(encoding="utf-8")
    rows = parse_rows(text.replace("| H16 |", "| H99 |"))
    rows["H3"] = {"summary": "", "tests": ["tests/test_real.py"], "status": "partial"}
    rows["H4"] = {"summary": "", "tests": [], "status": "done"}
    rows["H5"] = {"summary": "", "tests": ["tests/test_gone.py"], "status": "done"}
    found = final_problems(rows, tmp_path, {"tests/test_real.py"})
    assert "H16: no row" in found and "H3: partial" in found and "H4: no test" in found
    assert "H5: missing tests/test_gone.py" in found
