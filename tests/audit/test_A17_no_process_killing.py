"""A-17 (Medium): the old Stop scripts could kill an unrelated process. Nothing in the installer, the build, the tools or the
app kills a process or keeps a pid file, and there is no Stop script outside legacy/. The installer closes the app only
through Restart Manager (CloseApplications=yes), which closes the app's own files and nothing else (M14)."""
import re
import subprocess

from tests.conftest import ROOT

# A pid file is a name ending .pid in a string; self.pid (a person ID in the example-data generator) is not one.
KILL_RE = re.compile(r"\btaskkill\b|Stop-Process|\bpkill\b|\bkillall\b|\bwmic\b|(?<!self)\.pid['\")\s]|(?<!self)\.pid$|os\.kill\(|"
                     r"\bkill\s+-\d|\bkill\s+\$",
                     re.I)
DIRS = ("installer/", "build/", "tools/", "wholecount/")


def repo_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
                         capture_output=True, check=True).stdout.decode().split("\0")
    return [f for f in out if f]


def kill_lines(root, files):
    bad = []
    for f in files:
        if not f.startswith(DIRS):
            continue
        try:
            text = (root / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        bad += [(f, i) for i, line in enumerate(text.splitlines(), 1) if KILL_RE.search(line)]
    return bad


def test_nothing_kills_a_process_or_keeps_a_pid_file():
    assert kill_lines(ROOT, repo_files()) == []


def test_no_stop_script_outside_legacy():
    stops = [f for f in repo_files() if not f.startswith("legacy/") and f.rsplit("/", 1)[-1].lower().startswith("stop")]
    assert stops == []


def test_the_installer_closes_the_app_only_through_restart_manager():
    iss = (ROOT / "installer" / "wholecount.iss").read_text(encoding="utf-8")
    assert re.search(r"^CloseApplications=yes$", iss, re.M)


def test_negative_controls(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "x.ps1").write_text("Stop-Process -Name python\n")
    (tmp_path / "tools" / "y.sh").write_text("kill $(cat app.pid)\n")
    assert [f for f, _ in kill_lines(tmp_path, ["tools/x.ps1", "tools/y.sh"])] == ["tools/x.ps1", "tools/y.sh"]
