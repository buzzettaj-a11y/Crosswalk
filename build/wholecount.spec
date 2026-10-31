# -*- mode: python ; coding: utf-8 -*-
# Offline-hardened one-folder build of Wholecount (M14 section 2, research R4). Run from the repository root:
#   pyinstaller --noconfirm --clean --distpath dist --workpath build build/wholecount.spec
# The lists live in build/spec_lists.py so they can be tested without PyInstaller.
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))  # noqa: F821  SPECPATH is set by PyInstaller
# The package must be importable here, or collect_data_files and collect_submodules silently find nothing.
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "build"))
import spec_lists as L  # noqa: E402

WIN = sys.platform == "win32"

hidden = [
    "secrets", "hmac",                    # numpy's compiled random module imports them; static analysis can't see it
    "geosupport",                         # loaded only when Geosupport is found, by the backend's discover()
    "lxml.etree", "lxml._elementpath",    # pandas and openpyxl import these by name
]
# Stages, rules and readers are loaded by name, so every submodule is listed. The developer tools are excluded below.
hidden += [m for m in collect_submodules("wholecount") if m not in ("wholecount.dev", "wholecount.app_imports")]

datas = collect_data_files("wholecount", includes=["**/*.toml", "**/*.csv", "**/*.tsv", "**/*.xlsx", "**/*.xml", "**/*.geojson",
                                                   "**/*.json", "**/*.ttf", "**/*.txt"])
datas += collect_data_files("geosupport")      # python-geosupport reads its tables at import time
datas += [(os.path.join(ROOT, "licenses"), "licenses")]
if not any(dest.replace("\\", "/").startswith("wholecount/copy") for _src, dest in datas):
    raise SystemExit("BUILD FAILED: the copy registry was not collected")

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "wholecount", "__main__.py")],
    pathex=[ROOT],
    hiddenimports=hidden,
    datas=datas,
    runtime_hooks=[os.path.join(ROOT, "build", "rthook_offline.py")],
    excludes=L.EXCLUDES,
    noarchive=False,
)
a.binaries = L.drop(a.binaries, L.QT_DROP + (L.QT_DROP_WINDOWS if WIN else []))
a.datas = L.drop(a.datas, L.QT_DROP + (L.QT_DROP_WINDOWS if WIN else []))

# Build gate: fail the build, not the audit, if anything forbidden or any model file slipped into the tables.
bad = L.leaked(a.pure, a.binaries, a.datas) + L.model_files(a.datas, lambda p: os.path.getsize(p) if os.path.isfile(p) else 0)
if bad:
    raise SystemExit("OFFLINE GATE FAILED, forbidden entries in the build: " + ", ".join(bad))

icon = os.path.join(ROOT, "build", "wholecount.ico")
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, [], exclude_binaries=True, name="Wholecount", console=False, upx=False,
    icon=icon if os.path.exists(icon) else None,
    version=os.path.join(ROOT, "build", "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Wholecount")  # noqa: F821
