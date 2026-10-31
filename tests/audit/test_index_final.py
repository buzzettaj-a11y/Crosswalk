"""The audit index at the end of the rewrite (M15). Every High and Medium finding is done with a test that exists, is
collected, and isn't skipped or xfail everywhere. Every Low row is done or has a reason of a sentence or more."""
import re

import pytest

from tests.audit.test_index_complete import AUDIT_FILES, index_rows
from tests.conftest import ROOT
from tests.support.collect import always_off, collected


def audit_severities(root=ROOT):
    out = {}
    for f in AUDIT_FILES:
        text = (root / "docs" / "audit" / f).read_text(encoding="utf-8")
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            i = re.match(r"([ABC]-\d+)\.", block)
            sev = re.search(r"^- (?:\*\*)?Severity:(?:\*\*)? (\w+)", block, re.M)
            if i and sev:
                out[i.group(1)] = sev.group(1)
    return out


def final_problems(rows, severities, root, collected_files):
    found = []
    for sev in ("High", "Medium"):
        want = sum(1 for s in severities.values() if s == sev)
        have = sum(1 for r in rows.values() if r["severity"] == sev)
        if want != have:
            found.append(f"{sev}: {have} rows but the audit has {want}")
    for i, r in rows.items():
        if r["severity"] in ("High", "Medium") and r["status"] != "done":
            found.append(f"{i}: {r['severity']} and {r['status']}")
        if r["severity"] == "Low" and r["status"] != "done" and len(r.get("reason", "")) < 20:
            found.append(f"{i}: Low, not done and no reason")
        if r["status"] == "done":
            for t in r["tests"]:
                path = root / t
                if not path.is_file():
                    found.append(f"{i}: missing {t}")
                elif t not in collected_files:
                    found.append(f"{i}: {t} isn't collected")
                elif always_off(path.read_text(encoding="utf-8")):
                    found.append(f"{i}: {t} is skipped or xfail everywhere")
    return found


@pytest.fixture(scope="module")
def rows():
    return index_rows((ROOT / "tests" / "audit" / "INDEX.md").read_text(encoding="utf-8"))


def test_every_high_and_medium_finding_is_done_and_tested(rows):
    files = {t for r in rows.values() for t in r["tests"]}
    assert final_problems(rows, audit_severities(), ROOT, collected(files)) == []


def test_the_counts(rows):
    counts = {(s, st): sum(1 for r in rows.values() if r["severity"] == s and r["status"] == st)
              for s in ("High", "Medium", "Low") for st in ("done", "pending")}
    assert counts == {("High", "done"): 44, ("Medium", "done"): 40, ("Low", "done"): 17,
                      ("High", "pending"): 0, ("Medium", "pending"): 0, ("Low", "pending"): 0}


def test_negative_controls_on_a_copy(tmp_path, rows):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_off.py").write_text("import pytest\npytestmark = pytest.mark.skip('later')\n")
    (tmp_path / "tests" / "test_on.py").write_text("def test_x():\n    pass\n")
    bad = {"A-01": {"severity": "High", "status": "pending", "tests": []},
           "A-02": {"severity": "Medium", "status": "done", "tests": ["tests/test_off.py"]},
           "A-03": {"severity": "High", "status": "done", "tests": ["tests/test_gone.py"]},
           "A-04": {"severity": "High", "status": "done", "tests": ["tests/test_on.py"]},
           "C-27": {"severity": "Low", "status": "pending", "tests": []}}
    sev = {"A-01": "High", "A-02": "Medium", "A-03": "High", "A-04": "High", "A-05": "High", "C-27": "Low"}
    found = final_problems(bad, sev, tmp_path, {"tests/test_off.py"})
    assert "A-01: High and pending" in found
    assert "A-02: tests/test_off.py is skipped or xfail everywhere" in found
    assert "A-03: missing tests/test_gone.py" in found
    assert "A-04: tests/test_on.py isn't collected" in found
    assert "C-27: Low, not done and no reason" in found
    assert "High: 3 rows but the audit has 4" in found
