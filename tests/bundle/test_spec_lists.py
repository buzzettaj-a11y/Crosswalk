"""build/spec_lists.py stays in step with tools/offline_rules.py, and its two functions catch what they should (M14)."""
import spec_lists as L

from tools.offline_rules import FORBIDDEN_MODULES

# Forbidden names the build does not list in EXCLUDES, each for a reason. None at present: every forbidden module is
# excluded, the Qt ones included. A new entry needs a reason here.
EXCEPTIONS = frozenset()


def test_excludes_cover_every_forbidden_module():
    assert FORBIDDEN_MODULES - set(L.EXCLUDES) == EXCEPTIONS


def test_developer_tools_are_excluded():
    assert {"wholecount.dev", "wholecount.app_imports", "pip", "setuptools", "pytest"} <= set(L.EXCLUDES)


def test_leaked_flags_forbidden_entries_and_passes_a_clean_table():
    clean_pure = [("pandas", "x", "PYMODULE"), ("wholecount.engine.counts", "x", "PYMODULE")]
    clean_bin = [("PySide6/QtWidgets.abi3.so", "x", "EXTENSION"), ("libQt6Core.so.6", "x", "BINARY")]
    assert L.leaked(clean_pure, clean_bin, []) == []
    assert L.leaked([("PySide6.QtNetwork", "x", "PYMODULE")], [], []) == ["PySide6.QtNetwork"]
    assert L.leaked([("openai.client", "x", "PYMODULE")], [], []) == ["openai.client"]
    assert L.leaked([], [("lib-dynload/_socket.cpython-312-x86_64-linux-gnu.so", "x", "EXTENSION")], [])
    assert L.leaked([], [("libssl.so.3", "x", "BINARY")], [])
    assert L.leaked([], [], [("PySide6/Qt/lib/libQt6QtNetwork.so", "x", "DATA")])


def test_drop_removes_tls_and_generic_plugins():
    toc = [("PySide6/Qt/plugins/tls/libqopensslbackend.so", "x", "BINARY"),
           ("PySide6/Qt/plugins/generic/libqtuiotouchplugin.so", "x", "BINARY"),
           ("PySide6/Qt/plugins/platforms/libqoffscreen.so", "x", "BINARY")]
    assert [e[0] for e in L.drop(toc, L.QT_DROP)] == ["PySide6/Qt/plugins/platforms/libqoffscreen.so"]
    win = [("PySide6/Qt6Network.dll", "x", "BINARY"), ("PySide6/Qt6Core.dll", "x", "BINARY")]
    assert [e[0] for e in L.drop(win, L.QT_DROP_WINDOWS)] == ["PySide6/Qt6Core.dll"]


def test_model_files_are_caught(tmp_path):
    big = tmp_path / "w.bin"
    big.write_bytes(b"0" * (L.BIN_MAX + 1))
    small = tmp_path / "s.bin"
    small.write_bytes(b"0")
    datas = [("m/model.onnx", str(small), "DATA"), ("m/w.bin", str(big), "DATA"), ("m/ok.bin", str(small), "DATA")]
    import os
    assert L.model_files(datas, os.path.getsize) == ["m/model.onnx", "m/w.bin"]
