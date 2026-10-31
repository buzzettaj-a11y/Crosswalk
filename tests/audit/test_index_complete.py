"""SPEC 13.3: tests/audit/INDEX.md lists every audit finding with its README milestone, and every done row names tests that exist."""
import re

from tests.conftest import ROOT

AUDIT_FILES = ["A-claims.md", "B-values.md", "C-counts.md"]


def audit_ids(root=ROOT):
    ids = []
    for f in AUDIT_FILES:
        ids += re.findall(r"^### ([ABC]-\d+)\.", (root / "docs" / "audit" / f).read_text(encoding="utf-8"), re.M)
    return ids


def readme_milestones(text):
    """{audit ID: [milestone, ...]} from the README's order table."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\| (M\d\d) \|", line)
        if m:
            for i in re.findall(r"[ABC]-\d\d", line.split("|")[4]):
                out.setdefault(i, []).append(m.group(1))
    return out


def index_rows(text):
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"[ABC]-\d+", cells[0]):
            rows[cells[0]] = {"severity": cells[1], "milestones": [m.strip() for m in cells[2].split(",")],
                              "tests": re.findall(r"`([^`]+\.py)`", cells[3]), "status": cells[4]}
    return rows


def problems(ids, milestones, rows, root):
    found = [f"{i}: no row" for i in ids if i not in rows]
    found += [f"{i}: not an audit finding" for i in rows if i not in ids]
    for i, row in rows.items():
        if i in milestones and row["milestones"] != milestones[i]:
            found.append(f"{i}: milestone {row['milestones']} but README says {milestones[i]}")
        if row["severity"] not in ("High", "Medium", "Low"):
            found.append(f"{i}: bad severity")
        if row["status"] not in ("done", "pending"):
            found.append(f"{i}: bad status")
        if row["status"] == "done":
            if not row["tests"]:
                found.append(f"{i}: done with no test")
            found += [f"{i}: missing {t}" for t in row["tests"] if not (root / t).is_file()]
    return found


def test_index_lists_every_finding_with_its_milestone():
    ids = audit_ids()
    assert len(ids) == 101 and len(set(ids)) == 101
    milestones = readme_milestones((ROOT / "docs" / "milestones" / "README.md").read_text(encoding="utf-8"))
    rows = index_rows((ROOT / "tests" / "audit" / "INDEX.md").read_text(encoding="utf-8"))
    assert problems(ids, milestones, rows, ROOT) == []


def test_severities_match_the_audit_summary():
    rows = index_rows((ROOT / "tests" / "audit" / "INDEX.md").read_text(encoding="utf-8"))
    counts = {s: sum(r["severity"] == s for r in rows.values()) for s in ("High", "Medium", "Low")}
    assert counts == {"High": 44, "Medium": 40, "Low": 17}


def test_a20_is_done_with_its_test():
    row = index_rows((ROOT / "tests" / "audit" / "INDEX.md").read_text(encoding="utf-8"))["A-20"]
    assert row["status"] == "done" and row["milestones"] == ["M00", "M14"]
    assert "tests/audit/test_A20_no_launchers.py" in row["tests"]


def test_negative_controls(tmp_path):
    rows = index_rows(
        "| A-01 | High | M09 | arrives in M09 | pending |\n"
        "| A-02 | High | M01 | `tests/audit/test_gone.py` | done |\n"
        "| Z-99 | Low | M00 | | pending |\n"
    )
    found = problems(["A-01", "A-02", "A-03"], {"A-01": ["M09"], "A-02": ["M09"]}, rows, tmp_path)
    assert "A-03: no row" in found
    assert "A-02: milestone ['M01'] but README says ['M09']" in found
    assert "A-02: missing tests/audit/test_gone.py" in found
    assert not any(f.startswith("A-01") for f in found)
