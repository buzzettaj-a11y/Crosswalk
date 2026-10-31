"""The M09 dev commands print the counts the Windows checks expect."""
import subprocess
import sys

from tests.conftest import ROOT


def run(*args):
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", *args], capture_output=True, text=True, cwd=ROOT, timeout=300)
    assert p.returncode == 0, p.stderr
    return dict(line.rsplit(" ", 1) for line in p.stdout.splitlines())


def test_outputs_demo(tmp_path):
    base = run("outputs-demo", "--state", "base", "--out", str(tmp_path / "b"))
    assert base == {"clean_rows": "13", "review_rows": "8", "set_aside_rows": "1", "unique_clients_rows": "11",
                    "by_program_rows": "11", "files_written": "9"}
    dec = run("outputs-demo", "--state", "decided", "--out", str(tmp_path / "d"))
    assert (dec["clean_rows"], dec["review_rows"], dec["set_aside_rows"], dec["unique_clients_rows"]) == ("14", "0", "3", "13")
    assert run("outputs-demo", "--state", "base", "--practice", "--out", str(tmp_path / "p"))["files_written"] == "8"


def test_folder_check():
    assert run("folder-check", "--path", r"C:\Users\x\OneDrive\y") == {"folder_warning": "1"}
    assert run("folder-check", "--path", r"C:\Users\x\Documents") == {"folder_warning": "0"}
