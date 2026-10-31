"""Bundle tests read WHOLECOUNT_DIST (dist/Wholecount) and WHOLECOUNT_BUILD (build/wholecount). Without them they skip with
a clear message, unless WHOLECOUNT_REQUIRE_BUNDLE=1, when a missing folder fails the run (M14)."""
import os
import pathlib
import sys

import pytest

from tests.conftest import ROOT

sys.path.insert(0, str(ROOT / "build"))


def _folder(var):
    v = os.environ.get(var)
    if v and pathlib.Path(v).is_dir():
        return pathlib.Path(v)
    if os.environ.get("WHOLECOUNT_REQUIRE_BUNDLE") == "1":
        pytest.fail(f"{var} is not set to a built folder, and WHOLECOUNT_REQUIRE_BUNDLE=1")
    pytest.skip(f"{var} is not set; run make bundle and set {var} to test the built folder")


@pytest.fixture(scope="session")
def dist():
    return _folder("WHOLECOUNT_DIST")


@pytest.fixture(scope="session")
def build():
    return _folder("WHOLECOUNT_BUILD")
