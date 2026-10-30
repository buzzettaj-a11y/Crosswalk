"""SPEC 13.2: tests/HARD_RULES.md maps every hard rule H1 to H16 to its tests, and every test it names as existing does exist."""
import re

from tests.conftest import ROOT

STATUS_RE = re.compile(r"^(done|partial|arrives in M\d\d)$")


def parse_rows(text):
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"H\d+", cells[0]):
            rows[cells[0]] = {"summary": cells[1], "tests": re.findall(r"`([^`]+\.py)`", cells[2]), "status": cells[4]}
    return rows


def problems(rows, root):
    found = [f"H{n}: no row" for n in range(1, 17) if f"H{n}" not in rows]
    for rule, row in rows.items():
        if not STATUS_RE.match(row["status"]):
            found.append(f"{rule}: bad status {row['status']!r}")
        if row["status"] in ("done", "partial"):
            if not row["tests"]:
                found.append(f"{rule}: {row['status']} with no test")
            found += [f"{rule}: missing {t}" for t in row["tests"] if not (root / t).is_file()]
    return found


def test_every_hard_rule_has_a_row_and_its_tests_exist():
    assert problems(parse_rows((ROOT / "tests" / "HARD_RULES.md").read_text(encoding="utf-8")), ROOT) == []


def test_negative_controls(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text("")
    rows = parse_rows(
        "| H1 | a | `tests/test_real.py` | | done |\n"
        "| H2 | b | `tests/test_missing.py` | | partial |\n"
        "| H3 | c | | | done |\n"
        "| H4 | d | | | someday |\n"
    )
    found = problems(rows, tmp_path)
    assert "H2: missing tests/test_missing.py" in found
    assert "H3: done with no test" in found
    assert "H4: bad status 'someday'" in found
    assert "H16: no row" in found
    assert not any(f.startswith("H1:") for f in found)
