"""Geosupport's DLL imports no networking DLL that Joe hasn't reviewed (research Open risk 5). Skipped without Geosupport."""
import os
import pathlib
import sys

import pytest

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]
# Networking DLLs Joe has reviewed for the Geosupport DLL. Empty until its import table is read on a real install.
REVIEWED = frozenset()


def test_geosupport_dll_imports_no_unreviewed_networking_dll():
    from tools.pe_net_imports import NET_DLLS, imported_dlls
    from wholecount.guard.config import discover_geosupport_dirs

    dirs = discover_geosupport_dirs(os.environ, os.path.isdir)
    if not dirs:
        pytest.skip("Geosupport Desktop Edition is not installed")
    dll = pathlib.Path(dirs[0]) / "bin" / "NYCGEO.dll"
    found = imported_dlls(dll)
    print(sorted(found))
    assert sorted((found & NET_DLLS) - REVIEWED) == []
