"""The self-check (M14 section 3) under the guard, in a fresh python -I process as the research says."""
import json
import subprocess
import sys

import pytest

from tests.conftest import ROOT

RUN = r"""
import sys
sys.path.insert(0, %r)
sys.argv = ["Wholecount"] + %r
if %r:
    sys.stdout = None
    sys.stderr = None
import runpy
try:
    runpy.run_module("wholecount", run_name="__main__")
except SystemExit as e:
    raise SystemExit(e.code)
"""


def run(args, quiet=False):
    return subprocess.run([sys.executable, "-I", "-c", RUN % (str(ROOT), args, quiet)], capture_output=True, text=True,
                          timeout=600, env={"QT_QPA_PLATFORM": "offscreen", "PATH": "/usr/bin:/bin"})


@pytest.fixture(scope="module")
def checked(tmp_path_factory):
    out = tmp_path_factory.mktemp("sc") / "out"
    p = run(["--self-check", "--self-check-out", str(out)], quiet=True)
    return p, out


def test_every_check_is_ok_with_no_stdout_or_stderr(checked):
    p, out = checked
    assert p.returncode == 0, p.stderr
    data = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert data["checks"] and all(v == "ok" for v in data["checks"].values()), data["checks"]
    assert "pipeline.sample" in data["checks"] and "outputs.nine_files" in data["checks"] and "ui.build" in data["checks"]


def test_it_writes_only_result_json_and_files(checked):
    _, out = checked
    assert sorted(p.name for p in out.iterdir()) == ["files", "result.json"]
    assert len(list((out / "files").iterdir())) == 9


def test_counts_equal_expected(checked):
    _, out = checked
    plan = json.loads((ROOT / "wholecount" / "sample_data" / "EXPECTED.json").read_text(encoding="utf-8"))
    after = plan["counts"]["after_decisions"]
    c = json.loads((out / "result.json").read_text(encoding="utf-8"))["counts"]
    assert (c["counted"], c["not_counted_yet"], c["set_aside"], c["goal_1"], c["goal_2"], c["rows_received"]) == (
        after["counted"], after["not_counted_yet"], after["set_aside"], after["goal_1"]["high"], after["goal_2"]["high"],
        after["rows_received"])


def test_the_json_holds_no_value_from_the_example_files(checked):
    import csv
    _, out = checked
    text = (out / "result.json").read_text(encoding="utf-8")
    with open(ROOT / "wholecount" / "sample_data" / "example_clinic.csv", encoding="utf-8") as f:
        values = {v for row in csv.DictReader(f) for v in row.values() if v and len(v) >= 4}
    assert values and not [v for v in values if v in text]


def test_it_refuses_without_an_out_folder(tmp_path):
    p = run(["--self-check"])
    assert p.returncode == 2
    assert list(tmp_path.iterdir()) == []
