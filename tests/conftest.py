import os
import pathlib

# UI tests run headless. make test sets this too; setting it here covers a plain `python -m pytest` on Windows.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"
DEV_LOCK = ROOT / "requirements-dev.lock"
