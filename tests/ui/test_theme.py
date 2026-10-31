"""The theme (SPEC 11.2): tokens from the style guide, QSS rules, the bundled Archivo font, and no network fonts."""
import hashlib
import json
import re

import pytest

from tests.conftest import ROOT
from wholecount.ui.theme import resource_path, tokens
from wholecount.ui.theme.build_qss import build_qss

STYLE_GUIDE = ROOT / "docs" / "context" / "design" / "style-guide" / "tokens.json"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def token_colors():
    return {t["value"].lower() for t in tokens()["color"]["tokens"]}


def rules(qss):
    """(selector, body) pairs."""
    return re.findall(r"([^{}]+)\{([^{}]*)\}", qss)


def test_token_colors_match_the_style_guide():
    ours = {t["name"]: t["value"] for t in tokens()["color"]["tokens"]}
    theirs = {t["name"]: t["value"] for t in json.loads(STYLE_GUIDE.read_text(encoding="utf-8"))["color"]["tokens"]}
    assert ours == theirs
    assert tokens()["name"] == "Wholecount"


def test_every_color_is_a_token_or_white():
    used = {c.lower() for c in HEX.findall(build_qss(tokens()))}
    assert used <= token_colors() | {"#ffffff"}
    assert used


def _hue_is_red(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return r > 150 and r > g * 1.6 and r > b * 1.6


def test_no_radius_shadow_gradient_alpha_or_red():
    q = build_qss(tokens())
    assert not re.search(r"border-radius:\s*[1-9]", q)
    for bad in ("box-shadow", "gradient", "rgba(", "qlineargradient", "qradialgradient"):
        assert bad not in q
    assert not [c for c in HEX.findall(q) if _hue_is_red(c)]
    # negative control for the red check
    assert _hue_is_red("#d01010")


def test_borders_are_1px_except_3px_top_or_bottom():
    q = build_qss(tokens())
    for sel, body in rules(q):
        for prop, width in re.findall(r"(border(?:-[a-z]+)?):\s*(\d+)px", body):
            if width in ("0", "1"):
                continue
            if width == "2":
                assert ":focus" in sel or "flowBoxMemory" in sel, (sel, prop)
                continue
            assert width == "3" and prop in ("border-top", "border-bottom"), (sel, prop, width)


INTERACTIVE = ("QPushButton", "QLineEdit", "QComboBox", "QCheckBox")


@pytest.mark.parametrize("cls", INTERACTIVE)
def test_every_interactive_class_has_focus_and_hover(cls):
    q = build_qss(tokens())
    blue = next(t["value"] for t in tokens()["color"]["tokens"] if t["name"] == "blue-500")
    focus = [b for s, b in rules(q) if s.strip().startswith(cls) and ":focus" in s]
    assert focus and any(f"2px solid {blue}" in b for b in focus)
    assert any(s.strip().startswith(cls) and ":hover" in s for s, _ in rules(q))


def test_buttons_are_36px_tall():
    q = build_qss(tokens())
    base = [b for s, b in rules(q) if s.strip() == "QPushButton"]
    assert base and "min-height: 36px" in base[0]


def test_applied_qss_equals_build_qss(qapp):
    assert qapp.styleSheet() == build_qss(tokens())


def test_archivo_is_loaded_with_three_weights(qapp):
    from PySide6.QtGui import QFontDatabase

    assert "Archivo" in QFontDatabase.families()
    assert {"Regular", "SemiBold", "ExtraBold"} <= set(QFontDatabase.styles("Archivo"))
    assert qapp.font().family() == "Archivo"
    assert qapp.font().pixelSize() == 13


def test_font_failure_falls_back_and_logs_the_file_name_only(qapp, monkeypatch):
    from PySide6.QtGui import QFontDatabase

    from wholecount.ui.theme import apply

    status = dict(apply.FONT_STATUS)
    monkeypatch.setattr(QFontDatabase, "addApplicationFont", staticmethod(lambda p: -1))
    before = len(apply.RUN_LOG)
    assert apply.load_fonts() is False
    new = apply.RUN_LOG[before:]
    assert new and all(code == "font_failed" and name.endswith(".ttf") for code, name in new)
    del apply.RUN_LOG[before:]
    apply.FONT_STATUS.update(status)


def test_fonts_are_bundled_with_provenance():
    src = resource_path("fonts", "SOURCE.txt").read_text(encoding="utf-8")
    for name in ("Archivo-Regular.ttf", "Archivo-SemiBold.ttf", "Archivo-ExtraBold.ttf"):
        data = resource_path("fonts", name).read_bytes()
        assert hashlib.sha256(data).hexdigest() in src
    assert resource_path("fonts", "OFL.txt").exists()


def test_no_network_font_or_url_in_the_ui():
    for base in (ROOT / "wholecount", ROOT / "tools"):
        for p in base.rglob("*.py"):
            assert "fonts.googleapis" not in p.read_text(encoding="utf-8"), p
    for p in (ROOT / "wholecount" / "ui").rglob("*.py"):
        assert not re.search(r"https?:", p.read_text(encoding="utf-8")), p


def test_build_qss_cli_writes_the_text(tmp_path):
    from wholecount.ui.theme.build_qss import main

    out = tmp_path / "theme.qss"
    assert main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == build_qss(tokens())
