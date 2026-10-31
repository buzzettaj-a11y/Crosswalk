"""python -m wholecount.dev session-demo prints the R and S numbers the Windows checks expect, counts only."""
import subprocess
import sys

from tests.conftest import ROOT


def blocks():
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "session-demo"], capture_output=True, text=True, cwd=ROOT, timeout=300)
    assert p.returncode == 0, p.stderr
    out, cur = [], None
    for line in p.stdout.splitlines():
        k, v = line.rsplit(" ", 1)
        if k == "stage":
            cur = {}
            out.append(cur)
        cur[k] = int(v)
    assert "Ada" not in p.stdout and "Oak" not in p.stdout
    return out


def test_session_demo():
    b = blocks()
    base = {"received": 17, "counted": 13, "not_counted_yet": 3, "set_aside": 1, "goal1_low": 9, "goal1_high": 11, "goal2_low": 9,
            "goal2_high": 11, "open_copy_groups": 2, "confidence_level": 1, "balance_ok": 1}
    assert {k: b[0][k] for k in base} == base
    assert {k: b[1][k] for k in ("counted", "not_counted_yet", "set_aside", "goal1_low", "goal1_high", "confidence_level")} == {
        "counted": 14, "not_counted_yet": 0, "set_aside": 3, "goal1_low": 11, "goal1_high": 13, "confidence_level": 2}
    assert (b[2]["goal1_low"], b[2]["goal1_high"], b[2]["final"]) == (13, 13, 1)
    last = {k: v for k, v in b[-1].items() if k != "stage"}
    assert last == {k: v for k, v in b[0].items() if k != "stage"}
