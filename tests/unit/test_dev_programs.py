"""python -m wholecount.dev programs-demo and programs-check print counts only."""
import subprocess
import sys

from tests.conftest import ROOT


def run(*args):
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", *args], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_programs_demo():
    assert run("programs-demo").splitlines() == ["pairs_that_should_match 7", "pairs_matched 7", "pairs_that_should_not_match 27",
                                                 "pairs_left_alone 27", "chains_grouped 0"]


def test_programs_check(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text("Name,Program\nx,Workforce Dev.\ny,Workforce Development\nz,\nw,Youth\n", encoding="utf-8")
    one, two = run("programs-check", "--csv", str(a), "--column", "Program"), run("programs-check", "--csv", str(a))
    assert one == two
    got = dict(line.rsplit(" ", 1) for line in one.splitlines())
    assert (got["distinct_names"], got["proposals"], got["names_left_alone"], got["rows_without_program"]) == ("3", "1", "1", "1")
    assert "Workforce" not in one
