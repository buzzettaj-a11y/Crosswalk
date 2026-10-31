"""Windows-only tests (M14, SPEC 13.1). With WHOLECOUNT_REQUIRE_WINDOWS_TESTS=1 a skipped test fails the run, except the tests
named in SKIP_ALLOWED, which need Geosupport or a second account. A skip must never look green."""
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Test node names (file::test) allowed to skip in the required mode, each with its reason.
SKIP_ALLOWED = {
    "test_geosupport_installer_check.py::test_installer_log_matches_discover": "needs Geosupport Desktop Edition",
    "test_geosupport_imports.py::test_geosupport_dll_imports_no_unreviewed_networking_dll": "needs Geosupport Desktop Edition",
    "test_geosupport_real.py": "needs Geosupport Desktop Edition",
}


def _allowed(nodeid):
    name = nodeid.split("/")[-1]
    return name in SKIP_ALLOWED or name.split("::")[0] in SKIP_ALLOWED


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.skipped and os.environ.get("WHOLECOUNT_REQUIRE_WINDOWS_TESTS") == "1" and not _allowed(item.nodeid):
        rep.outcome = "failed"
        rep.longrepr = f"skipped in required mode: {rep.longrepr}"


def installer():
    out = sorted((ROOT / "Output").glob("Wholecount-Setup-*.exe"))
    if not out:
        pytest.skip("no installer in Output; run tools\\build.ps1 or the Windows workflow first")
    return out[-1]


def dist():
    d = os.environ.get("WHOLECOUNT_DIST")
    if not d or not pathlib.Path(d).is_dir():
        pytest.skip("WHOLECOUNT_DIST is not set to a built folder")
    return pathlib.Path(d)
