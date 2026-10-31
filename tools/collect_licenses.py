"""Writes licenses/: one file per approved runtime distribution, the Python license, the PyInstaller bootloader license, the
Qt LGPL notice, the Archivo OFL and the NYC data notice (M14 section 2). Run in the build venv. It reads installed files only."""
import importlib.metadata as md
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "licenses"
sys.path.insert(0, str(ROOT))

from tools.offline_rules import APPROVED_DISTS  # noqa: E402

NAMES = ("LICENSE", "LICENCE", "COPYING", "NOTICE")

LGPL_NOTICE = """Qt for Python (PySide6-Essentials and shiboken6)

Wholecount uses Qt for Python under the GNU Lesser General Public License version 3 (LGPL 3).
The Qt libraries are separate files in the _internal folder of this installation, so you may replace them with your own
build of the same version. The Qt source code is available from The Qt Company and the Qt Project. Ask the publisher of
this copy of Wholecount if you want a copy of the source for the version shipped here.
"""


def _dist_text(dist):
    parts = []
    for f in sorted(dist.files or [], key=str):
        if any(k in pathlib.PurePath(str(f)).name.upper() for k in NAMES) and ".dist-info" in str(f):
            try:
                parts.append(f"==> {pathlib.PurePath(str(f)).name}\n" + f.locate().read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    meta = dist.metadata
    head = f"{meta['Name']} {dist.version}\nLicense: {meta.get('License-Expression') or meta.get('License') or 'see below'}\n\n"
    return head + ("\n\n".join(parts) if parts else "No license file is included in this package's distribution. The "
                   "license named above applies.\n")


def _python_license():
    for c in (pathlib.Path(sys.base_prefix) / "LICENSE.txt", pathlib.Path(sys.base_prefix) / "lib" / "python3.12" / "LICENSE.txt",
              pathlib.Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"):
        if c.exists():
            return c.read_text(encoding="utf-8", errors="replace")
    return f"Python {sys.version.split()[0]}\nLicense: Python Software Foundation License Version 2.\n"


def _nyc_notice():
    import csv

    with open(ROOT / "wholecount" / "engine" / "geo" / "data" / "nyc_zips.csv", encoding="utf-8") as f:
        sources = sorted({row["source"] for row in csv.DictReader(f)})
    lines = ["NYC reference data shipped with Wholecount", "", "ZIP code table (wholecount/engine/geo/data/nyc_zips.csv):"]
    lines += [f"  Source: {s}" for s in sources]
    lines += ["", "District boundary files: none are shipped in this build. See the README in the districts folder."]
    return "\n".join(lines) + "\n"


def files():
    """{file name: text} for every license file."""
    out = {}
    for d in sorted(APPROVED_DISTS):
        out[f"{d}.txt"] = _dist_text(md.distribution(d))
    out["python.txt"] = _python_license()
    out["pyinstaller-bootloader.txt"] = _dist_text(md.distribution("pyinstaller"))
    out["PySide6-LGPL-NOTICE.txt"] = LGPL_NOTICE
    out["archivo-OFL.txt"] = (ROOT / "wholecount" / "ui" / "theme" / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    out["NYC-DATA-NOTICE.txt"] = _nyc_notice()
    return out


def main():
    OUT.mkdir(exist_ok=True)
    for name, text in files().items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(len(list(OUT.iterdir())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
