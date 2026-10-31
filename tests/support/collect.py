"""Which test files pytest collects, without running them (M15 final ledgers)."""
import re
import subprocess
import sys

from tests.conftest import ROOT


def collected(files):
    """The subset of the given repo-relative test files from which pytest collects at least one test."""
    files = sorted(set(files))
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *files], cwd=ROOT,
                       capture_output=True, text=True, timeout=600)
    seen = {m.group(1) for m in re.finditer(r"^([\w/.-]+\.py)::", p.stdout, re.M)}
    return {f for f in files if f in seen}


ALWAYS_OFF = re.compile(r"pytest\.mark\.xfail|pytestmark\s*=\s*pytest\.mark\.skip\(|^@pytest\.mark\.skip\(|pytest\.skip\(\s*['\"]",
                        re.M)


def always_off(text):
    """True when a test module is xfail, or skipped with no condition, on every platform."""
    return bool(ALWAYS_OFF.search(text))
