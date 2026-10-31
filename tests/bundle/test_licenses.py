"""licenses/ has one file per approved runtime distribution, plus the Python, bootloader, LGPL, OFL and NYC data notices."""
from tests.conftest import ROOT
from tools.offline_rules import APPROVED_DISTS

LIC = ROOT / "licenses"


def test_one_file_per_approved_distribution():
    assert [d for d in sorted(APPROVED_DISTS) if not (LIC / f"{d}.txt").is_file()] == []


def test_the_notices_are_present():
    for n in ("python.txt", "pyinstaller-bootloader.txt", "PySide6-LGPL-NOTICE.txt", "archivo-OFL.txt", "NYC-DATA-NOTICE.txt"):
        assert (LIC / n).is_file(), n
    assert "LGPL" in (LIC / "PySide6-LGPL-NOTICE.txt").read_text(encoding="utf-8")


def test_negative_control(tmp_path):
    missing = [d for d in sorted(APPROVED_DISTS | {"made-up-dist"}) if not (LIC / f"{d}.txt").is_file()]
    assert missing == ["made-up-dist"]
