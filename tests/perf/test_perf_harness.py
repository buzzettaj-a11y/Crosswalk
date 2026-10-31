"""The perf command and the report (SPEC 15, M15). The command runs in a subprocess, because it installs the offline guard,
and its output is counts only: integer labels and one backend word."""
import json
import re
import shutil
import subprocess
import sys

import pytest

from tests.conftest import ROOT
from tools import make_large_set, perf_report

LABELS = {"add_files_ms", "process_ms", "preview_ms", "decision_ms", "download_ms", "redraw_max_ms", "peak_memory_mb", "rows",
          "files"}


@pytest.fixture(scope="module")
def small_run(tmp_path_factory):
    folder = tmp_path_factory.mktemp("perfset")
    truth = make_large_set.write_set(20261030, 600, 5, folder)
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "perf", "--set", str(folder), "--fake", "--report",
                        str(folder / "perf-report.txt")], cwd=ROOT,
                       capture_output=True, text=True, timeout=600, env={**__import__("os").environ,
                                                                          "QT_QPA_PLATFORM": "offscreen"})
    assert p.returncode == 0, p.stderr
    return folder, truth, p.stdout


def test_output_is_integer_labels_and_one_backend_word(small_run):
    _, truth, out = small_run
    lines = out.strip().splitlines()
    assert lines[-1] == "backend fake"
    values = {}
    for line in lines[:-1]:
        assert re.fullmatch(r"[a-z_]+ \d+", line), line
        k, v = line.split()
        values[k] = int(v)
    assert set(values) == LABELS
    assert values["rows"] == truth["rows"] and values["files"] == 5


def test_no_client_value_is_printed(small_run):
    folder, _, out = small_run
    words = set()
    for name in make_large_set.FIRST + make_large_set.LAST:
        words.add(name)
    assert not [w for w in words if re.search(rf"\b{re.escape(w)}\b", out)]
    assert str(folder) not in out


def test_the_report_marks_a_fake_process_time_not_accepted(small_run):
    folder, _, out = small_run
    written = (folder / "perf-report.txt").read_text(encoding="utf-8")
    assert written.startswith("Backend: fake") and "not accepted" in written
    values, backend = perf_report.parse(out)
    rows = {r[1]: r for r in perf_report.rows(values, backend)}
    assert rows["process_ms"][4] == "not accepted"
    assert rows["startup_ms"][4] == "not measured"
    assert rows["add_files_ms"][4] in ("ok", "over")
    text = perf_report.render(values, backend)
    assert "fake geocoder" in text


def test_ok_over_and_alarms():
    values = {"add_files_ms": 10001, "preview_ms": 10, "process_ms": 50}
    rows = {r[1]: r[4] for r in perf_report.rows(values, "geosupport")}
    assert rows["add_files_ms"] == "over" and rows["preview_ms"] == "ok" and rows["process_ms"] == "ok"
    assert perf_report.alarms({"preview_ms": 16, "download_ms": 15}, {"preview_ms": 10, "download_ms": 10}) == ["preview_ms"]


def test_the_baseline_names_known_labels():
    base = json.loads((ROOT / "tests" / "perf" / "baseline.json").read_text(encoding="utf-8"))
    assert set(base) <= LABELS and all(isinstance(v, int) and v >= 0 for v in base.values())


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_make_perf_builds_the_set_runs_and_reports():
    p = subprocess.run(["make", "-n", "perf", "PERF_FLAGS=--fake"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    lines = [ln.strip() for ln in p.stdout.splitlines() if not ln.startswith("make")]
    assert lines == ["python tools/make_large_set.py --out build/perf-set",
                     "python -m wholecount.dev perf --set build/perf-set --fake > build/perf-out.txt",
                     "python tools/perf_report.py build/perf-out.txt --out build/perf-report.txt"]


def test_ci_perf_job_never_fails_the_run():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci.split("\n  perf:\n", 1)[1]
    assert "continue-on-error: true" in job
    assert "PERF_FLAGS=--fake" in job and "--baseline tests/perf/baseline.json --github" in job
