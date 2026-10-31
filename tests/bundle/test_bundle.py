"""The built folder and PyInstaller's tables (M14, SPEC 12.1 layer 3). Needs WHOLECOUNT_DIST and WHOLECOUNT_BUILD."""
import sys

import pytest

from tests.conftest import ROOT
from tools import check_bundle as cb
from tools.offline_rules import APPROVED_DISTS


def test_no_forbidden_python_modules_in_pyz_or_extensions(build):
    names = cb.pyz_modules(build) | set(cb.extension_modules(cb.collect_names(build)))
    assert cb.forbidden_modules(names) == []
    assert "wholecount.engine.counts" in names


def test_no_forbidden_files_in_output_folder(dist):
    assert cb.forbidden_files(cb.files(dist)) == []


def test_no_model_or_pickle_files_in_output_folder(dist):
    assert cb.model_files(dist) == []


def test_no_large_bin_files(dist):
    assert [p for p in dist.rglob("*.bin") if p.stat().st_size > 1024 * 1024] == []


def test_warn_file_shows_exclusions_not_inclusions(build):
    warn = cb.warn_inclusions(build)
    excluded = {n for kind, n in warn if kind == "excluded"}
    assert "socket" in excluded and "PySide6.QtNetwork" in excluded


def test_required_files_present(dist):
    files = set(cb.files(dist))
    base = "_internal/wholecount/"
    need = [base + "copy/en.toml", base + "settings/identity.toml", base + "engine/geo/data/nyc_zips.csv",
            base + "ui/theme/fonts/OFL.txt", base + "sample_data/EXPECTED.json", base + "sample_data/sample_reference.csv",
            "_internal/licenses/PySide6-LGPL-NOTICE.txt"]
    need += [f"_internal/wholecount/sample_data/{n}" for n in ("example_clinic.csv", "example_housing.xlsx",
                                                              "example_partner.tsv", "example_portal.json",
                                                              "example_state.xml")]
    need += [f"_internal/licenses/{d}.txt" for d in sorted(APPROVED_DISTS)]
    assert [n for n in need if n not in files] == []
    fonts = [f for f in files if f.startswith(base + "ui/theme/fonts/") and f.endswith(".ttf")]
    assert len(fonts) >= 3
    assert any(f.startswith(base + "engine/geo/data/districts/") for f in files)


def test_nothing_unwanted_shipped(dist):
    assert cb.unwanted(cb.files(dist)) == []


def test_negative_controls(tmp_path):
    assert cb.unwanted(["_internal/tests/x.py", "README.md", "_internal/licenses/a.md", "run.bat",
                        "_internal/wholecount/dev.py"]) == ["README.md", "_internal/tests/x.py", "_internal/wholecount/dev.py",
                                                            "run.bat"]
    assert cb.forbidden_files(["_internal/lib-dynload/_ssl.cpython-312.so", "_internal/ok.so"]) == \
        ["_internal/lib-dynload/_ssl.cpython-312.so"]
    assert cb.forbidden_files(["_internal/PySide6/Qt6Network.dll", "_internal/x.dll"]) == ["_internal/PySide6/Qt6Network.dll"]
    assert cb.forbidden_modules({"socket", "urllib.request", "pandas", "socketx"}) == ["socket", "urllib.request"]
    assert cb.extension_modules(["lib-dynload/_socket.cpython-312-x86_64-linux-gnu.so", "PySide6/QtCore.pyd",
                                 "libQt6Core.so.6"]) == ["_socket", "PySide6.QtCore"]
    (tmp_path / "m.onnx").write_bytes(b"x")
    assert cb.model_files(tmp_path) == ["m.onnx"]


@pytest.mark.skipif(sys.platform != "win32", reason="the PE subsystem and version resource are Windows files")
def test_exe_is_windowed(dist):
    import pefile
    pe = pefile.PE(str(dist / "Wholecount.exe"), fast_load=True)
    assert pe.OPTIONAL_HEADER.Subsystem == 2       # IMAGE_SUBSYSTEM_WINDOWS_GUI


@pytest.mark.skipif(sys.platform != "win32", reason="the version resource is in the Windows exe")
def test_version_resource_matches_brand(dist):
    import pefile

    from wholecount.brand import VERSION
    pe = pefile.PE(str(dist / "Wholecount.exe"))
    strings = {}
    for fi in getattr(pe, "FileInfo", []):
        for entry in fi:
            for st in getattr(entry, "StringTable", []):
                strings.update({k.decode(): v.decode() for k, v in st.entries.items()})
    assert strings.get("ProductVersion") == VERSION and strings.get("ProductName") == "Wholecount"


def test_version_info_text_matches_brand():
    from tools.make_version_info import render
    from wholecount.brand import VERSION
    text = render()
    assert f"StringStruct('ProductVersion', '{VERSION}')" in text and "Wholecount.exe" in text
    assert (ROOT / "build" / "wholecount.spec").read_text(encoding="utf-8").count("console=False") == 1
