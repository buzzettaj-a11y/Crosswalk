"""ConfidenceBlock (SPEC 7.4, 11.7): level and reason from the engine, measures from confidence.toml, the Low tick."""
import pytest
from PySide6.QtWidgets import QLabel

from tools import screen_fixtures as F
from wholecount import copy
from wholecount.ui.theme import color
from wholecount.ui.widgets.confidence import ConfidenceBlock, ConfidencePopover, measure_rows


def block(qtbot, view, **kw):
    b = ConfidenceBlock(view, **kw)
    qtbot.addWidget(b)
    return b


@pytest.mark.parametrize("level,tone", [("high", "ink"), ("medium", "amber"), ("low", "amber")])
def test_level_word_and_color(qtbot, level, tone):
    b = block(qtbot, F.after_run(confidence=F.confidence(level)))
    assert b.level.text() == copy.get(f"confidence.level.{level}")
    assert b.level.property("tone") == tone
    assert "%" not in b.headline()


def test_reason_is_the_engines_sentence(qtbot):
    from wholecount.session.frame import confidence_reason

    v = F.after_run(confidence=F.confidence("low"))
    b = block(qtbot, v)
    assert b.reason.text() == confidence_reason(v.confidence)
    assert b.headline() == "Low. 6,084 of 7,412 rows are counted, and 14 possible same-person pairs are still open."


@pytest.mark.claim("CL-CONF-NEEDS-01")
@pytest.mark.claim("CL-CONF-NEEDS-02")
def test_measures_read_thresholds_from_the_view(qtbot):
    v = F.after_run(confidence=F.confidence("low"))
    rows = measure_rows(v.confidence)
    assert rows[0][:3] == ("Rows counted", "6,084 of 7,412", "High needs 95%. Under 80% is Low.")
    assert rows[0][3] is True and rows[2][3] is False
    assert rows[1][2] == "High needs no more than 0 open. Open pairs never make it Low."
    changed = v.confidence.__class__(**{**v.confidence.__dict__, "thresholds": {**v.confidence.thresholds,
                                                                                  "high_counted_pct": 90, "low_pct": 70}})
    assert measure_rows(changed)[0][2] == "High needs 90%. Under 70% is Low."


@pytest.mark.claim("CL-CONF-NEEDS-01")
@pytest.mark.claim("CL-CONF-NEEDS-02")
def test_thresholds_come_from_confidence_toml(tmp_path, monkeypatch):
    """A changed toml changes both the engine's level and the measure text the screen shows."""
    from tests.support.session import base
    from wholecount.settings import loader
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    real = loader.load

    def fake(name, *a, **k):
        d = real(name, *a, **k)
        if name == "confidence":
            d = {**d, "batch": {**d["batch"], "high_counted_pct": 72, "low_pct": 41, "high_open_pairs": 3}}
        return d
    monkeypatch.setattr(loader, "load", fake)
    import wholecount.engine.confidence as ec
    monkeypatch.setattr(ec, "load", fake)
    v = build_view(s)
    rows = measure_rows(v.confidence)
    assert rows[0][2] == "High needs 72%. Under 41% is Low."
    assert rows[1][2] == "High needs no more than 3 open. Open pairs never make it Low."
    assert v.confidence.thresholds["high_placed_pct"] == real("confidence")["batch"]["high_placed_pct"]


def test_no_geocoder_reads_not_available_with_the_engines_reason(qtbot):
    v = F.after_run(confidence=F.confidence("medium", placed=False))
    rows = measure_rows(v.confidence)
    assert rows[2][1] == "not available" and rows[2][3] is True
    b = block(qtbot, v)
    assert "Addresses weren't placed, so confidence can't be High." in b.reason.text()


def test_calibration_line_only_when_set(qtbot):
    v = F.after_run()
    p = ConfidencePopover(v.confidence)
    qtbot.addWidget(p)
    assert p.calibration is None
    v2 = F.after_run(confidence=F.confidence("medium", calibration=("2026-10-01", "fake rates")))
    p2 = ConfidencePopover(v2.confidence)
    qtbot.addWidget(p2)
    assert p2.calibration.text() == "Measured on 2026-10-01: fake rates"


def test_popover_opens_from_the_link(qtbot):
    b = block(qtbot, F.after_run())
    b.show()
    pop = b.open_popover()
    assert [r[0] for r in pop.rows] == ["Rows counted", "Same-person pairs open", "Addresses placed with high confidence"]
    assert pop.rows[1][1].property("tone") == "amber"


@pytest.mark.claim("CL-CONF-TICK-01")
def test_low_tick_dispatches_and_resets_on_recompute(tmp_path, qtbot, qapp):
    from tests.support.session import base, rk
    from tests.ui.conftest import settle
    from wholecount.session import commands as C
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = base(tmp_path)
    assert s.results.confidence.level == "low"
    bridge = SessionBridge(s)
    w = MainWindow(bridge, clock=lambda: F.NOW, confirm=lambda *a: True)
    qtbot.addWidget(w)
    w.show()
    settle(qapp)
    tick = w.ledger.conf_block.tick
    assert tick is not None and not tick.check.isChecked()
    assert "low_confidence_unacked" in s.download_gate().reasons
    tick.check.setChecked(True)
    settle(qapp)
    assert isinstance(s.history.stack[-1], C.AcknowledgeLowConfidence)
    assert "low_confidence_unacked" not in s.download_gate().reasons
    assert w.ledger.conf_block.tick.check.isChecked()
    assert any(e.code == "LOW_CONFIDENCE_ACKNOWLEDGED" for e in s.audit)
    bridge.dispatch(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    settle(qapp)
    if s.results.confidence.level == "low":
        assert not w.ledger.conf_block.tick.check.isChecked()
        assert "low_confidence_unacked" in s.download_gate().reasons
    w.closing_confirmed = True


def test_no_green_and_no_percent_in_the_block(qtbot):
    for level in ("high", "medium", "low"):
        b = block(qtbot, F.after_run(confidence=F.confidence(level)))
        tones = {w.property("tone") for w in b.findChildren(QLabel)}
        assert "green" not in tones
        assert "%" not in b.headline()
    assert color("green-500") not in open(__file__, encoding="utf-8").read()
