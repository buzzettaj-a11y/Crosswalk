"""Run a session over literal CSV files or audit fixtures, with low confidence acknowledged, for M09 audit tests."""
import csv
import shutil

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from wholecount.session import commands as C
from wholecount.session.runner import process

AUDIT_FIXTURES = ROOT / "docs" / "audit" / "A-fixtures"


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def fixture(tmp_path, *names):
    (tmp_path / "in").mkdir(parents=True, exist_ok=True)
    return [shutil.copy(AUDIT_FIXTURES / n, tmp_path / "in" / n) for n in names]


def run(tmp_path, paths, **kw):
    s = r_fixture.session(tmp_path, paths=paths, **kw)
    process(s)
    ack(s)
    return s


def ack(s):
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    return s
