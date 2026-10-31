"""python -m wholecount.dev people-demo prints the C-01 numbers the Windows checks expect, counts only."""
import subprocess
import sys

from tests.conftest import ROOT


def test_people_demo_numbers():
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "people-demo"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr
    got = dict(line.rsplit(" ", 1) for line in p.stdout.splitlines())
    assert {k: got[k] for k in ("automatic_joins", "joins_four_exact_facts", "joins_same_system_id", "proposals_likely",
                                "proposals_possible", "people_low", "people_high", "master_ids_unique")} == {
        "automatic_joins": "1", "joins_four_exact_facts": "1", "joins_same_system_id": "0", "proposals_likely": "4",
        "proposals_possible": "0", "people_low": "7", "people_high": "11", "master_ids_unique": "1"}
    for name in ("Maria", "Rodriguez", "Grand", "1985"):
        assert name not in p.stdout


def test_people_check_twice_is_identical(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text("Client_ID,First_Name,Last_Name,Date_of_Birth,Address_1,Zip,Program\n"
                 "1,Ana,Perez,1990-05-06,7 Elm St,11201,Housing\n1,Beth,Perez,1994-09-09,5 Oak Ave,11201,Housing\n"
                 "2,Cy,Kim,1992-02-02,9 Elm St,11201,Youth\n", encoding="utf-8")
    b = tmp_path / "b.csv"
    b.write_text("Client_ID,First_Name,Last_Name,Date_of_Birth,Address_1,Zip,Program\n"
                 "77,Cy,Kim,1992-02-02,9 Elm St,11201,Housing\n", encoding="utf-8")
    cmd = [sys.executable, "-m", "wholecount.dev", "people-check", "--csv", str(a), "--csv", str(b), "--system", "A", "--system", "B"]
    one = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120)
    two = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert one.returncode == 0 and one.stdout == two.stdout
    got = dict(line.rsplit(" ", 1) for line in one.stdout.splitlines())
    assert got["copy_groups_same_id_different"] == "1" and got["automatic_joins"] == "1" and got["rows_read"] == "4"
    assert "Perez" not in one.stdout
