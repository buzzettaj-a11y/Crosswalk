"""SPEC 12.1 layer 4: install_for_app finds the Geosupport install and allows any DLL inside it, and nothing else."""
import ctypes.util
import os
import pathlib
import shutil

import pytest

from tests.support.guarded import run_guarded
from wholecount.guard.config import discover_geosupport_dirs

BS = "\\"


def test_discover_from_geofiles_and_the_default_folder():
    home = r"C:\Program Files\Geosupport Desktop Edition"
    assert discover_geosupport_dirs({"GEOFILES": home + r"\fls" + BS}, lambda p: True)[0] == home
    assert discover_geosupport_dirs({}, lambda p: p == home) == (home,)
    assert discover_geosupport_dirs({}, lambda p: False) == ()


def test_empty_geofiles_turns_it_off():
    assert discover_geosupport_dirs({"GEOFILES": ""}, lambda p: True) == ()


def test_the_same_folder_is_listed_once():
    home = r"C:\Program Files\Geosupport Desktop Edition"
    assert discover_geosupport_dirs({"GEOFILES": home.lower() + r"\Fls"}, lambda p: True) == (home.lower(),
                                                                                                r"C:\Program Files (x86)\Geosupport Desktop Edition")


def _a_shared_library():
    name = ctypes.util.find_library("m")
    for d in ("/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu", "/lib64", "/usr/lib64", "/lib", "/usr/lib"):
        if name and pathlib.Path(d, name).exists():
            return pathlib.Path(d, name)
    return None


@pytest.mark.skipif(os.name == "nt" or _a_shared_library() is None, reason="needs a POSIX shared library to copy")
def test_dll_inside_the_install_loads_and_another_is_denied(tmp_path):
    lib = _a_shared_library()
    install = tmp_path / "Geosupport Desktop Edition 25C"
    (install / "bin").mkdir(parents=True)
    (install / "fls").mkdir()
    shutil.copy(lib, install / "bin" / "nycgeo.so")
    other = tmp_path / "elsewhere"
    other.mkdir()
    shutil.copy(lib, other / "nycgeo.so")
    env = dict(os.environ, GEOFILES=str(install / "fls") + "/")
    r = run_guarded(f"""
        import ctypes
        attempt('inside', lambda: ctypes.CDLL({str(install / 'bin' / 'nycgeo.so')!r}))
        attempt('outside', lambda: ctypes.CDLL({str(other / 'nycgeo.so')!r}))
    """, install="guard.install_for_app()", env=env)
    assert r == {"inside": "NOT BLOCKED", "outside": "blocked"}, r


def test_without_an_install_no_path_is_allowed(tmp_path):
    env = dict(os.environ, GEOFILES="")
    r = run_guarded("""
        attempt('path', lambda: sys.audit('ctypes.dlopen', '/opt/Geosupport/bin/nycgeo.dll'))
        attempt('bare', lambda: sys.audit('ctypes.dlopen', 'nycgeo'))
    """, install="guard.install_for_app()", env=env)
    assert set(r.values()) == {"blocked"}, r
