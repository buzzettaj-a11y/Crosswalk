"""M13's dev commands print counts and fixed labels only (H8). In a subprocess, because importing dev installs the guard."""
import os
import subprocess
import sys

from tests.conftest import ROOT
from tests.support import crosswalk as X
from tests.support.secrets import TEST_SECRET


def dev(args, data_dir):
    env = {**os.environ, "WHOLECOUNT_DATA_DIR": str(data_dir), "PYTHONPATH": str(ROOT)}
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", *args], cwd=ROOT, capture_output=True, text=True, timeout=180,
                       env=env)
    assert p.returncode == 0, p.stderr
    return dict(line.rsplit(" ", 1) for line in p.stdout.strip().splitlines())


def test_crosswalk_check(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "key.bin").write_bytes(TEST_SECRET)
    s = X.session(tmp_path / "b1", data / "crosswalk.db", ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    out = dev(["crosswalk-check"], data)
    assert out == {"people": "10", "person_keys": "12", "pair_verdicts": "4", "program_groups": "0", "merged": "0",
                   "cell_values_found": "0", "wal_files": "0"}


def test_calibration_check_with_nothing_saved(tmp_path):
    assert dev(["calibration-check"], tmp_path / "data") == {"labeled_pairs": "0", "cell_values_found": "0",
                                                            "regression_dropped": "0"}
