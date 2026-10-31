"""Held controls and the run hold (SPEC 11.3). A held control stays focusable, says what releases it, and ignores clicks."""
import ast

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit

from tests.conftest import ROOT
from tools import screen_fixtures as F
from wholecount import copy
from wholecount.ui.widgets.held import HeldAction, HoldReason, RunHold


def test_held_button_is_styled_captioned_focusable_and_silent(qtbot):
    a = HeldAction("action.process")
    qtbot.addWidget(a)
    a.show()
    fired = []
    a.clicked.connect(lambda: fired.append(1))
    a.set_hold(HoldReason("hold.demo"))
    assert a.button.property("kind") == "held"
    assert a.caption.isVisible() and a.caption.text() == copy.get("hold.demo")
    assert a.button.accessibleDescription() == copy.get("hold.demo")
    assert a.button.isEnabled() and a.button.focusPolicy() != Qt.NoFocus
    qtbot.mouseClick(a.button, Qt.LeftButton)
    assert fired == []
    a.set_hold(None)
    assert a.button.property("kind") == "primary" and not a.caption.isVisible()
    qtbot.mouseClick(a.button, Qt.LeftButton)
    assert fired == [1]


def test_run_hold_wins_then_the_first_listed_hold(qtbot):
    a = HeldAction("action.process")
    qtbot.addWidget(a)
    a.set_holds([HoldReason("hold.demo"), HoldReason("strip.cap.not_run")])
    assert a.hold.copy_id == "hold.demo"
    a.set_run_hold(True)
    assert a.hold.copy_id == "hold.run"
    a.set_run_hold(False)
    assert a.hold.copy_id == "hold.demo"


@pytest.mark.claim("CL-HOLD-RUN-01")
def test_run_hold_holds_every_registered_control_and_restores_each(qtbot):
    rh = RunHold()
    a = HeldAction("action.process")
    b = HeldAction("action.process")
    b.set_hold(HoldReason("hold.demo"))
    box, combo, line = QCheckBox("x"), QComboBox(), QLineEdit()
    combo.addItems(["one", "two"])
    line.setReadOnly(False)
    for w in (a, b, box, combo, line):
        qtbot.addWidget(w)
        w.show()
        rh.register(w)
    rh.hold()
    assert a.hold.copy_id == "hold.run" and b.hold.copy_id == "hold.run"
    assert box.property("held") is True and box.accessibleDescription() == copy.get("hold.run")
    qtbot.mouseClick(box, Qt.LeftButton)
    assert not box.isChecked()
    assert line.isReadOnly()
    assert box.focusPolicy() != Qt.NoFocus
    rh.release()
    assert a.hold is None and b.hold.copy_id == "hold.demo"
    assert not line.isReadOnly() and box.accessibleDescription() == ""
    qtbot.mouseClick(box, Qt.LeftButton)
    assert box.isChecked()


def test_window_hold_leaves_navigation_and_help_live(make_window, qtbot, qapp):
    from tests.ui.conftest import settle

    w = make_window(F.after_run(), stage="run")
    w.run_hold.hold()
    registered = set(map(id, w.run_hold.registered()))
    for live in (w.ledger.your_data, w.ledger.check_line, *w.strip.items.values(), w.band.details_button,
                 w.ticker.all_button, w.ticker.cancel_button):
        assert id(live) not in registered
    assert w.strip.undo.held
    qtbot.mouseClick(w.strip.items["summary"], Qt.LeftButton)
    settle(qapp)
    assert w.current == "summary"
    w.run_hold.release()


# The static scan: every UI class that fires a command registers with the run hold, or is listed here with a reason.
ALLOWLIST = {
    "wholecount/ui/frame/bridge.py": "the bridge itself runs commands",
    "wholecount/ui/frame/window.py": "routes Undo, the reviewer change and the Low tick; each control registers in __init__",
    "wholecount/ui/widgets/confidence.py": "the Low tick only emits; the window dispatches and the ledger is held as a whole",
}


def _fires(src):
    return any(s in src for s in (".dispatch(", ".undo(", "history.execute("))


def test_every_command_firing_class_is_registered_or_allowlisted():
    bad = []
    for p in sorted((ROOT / "wholecount" / "ui").rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        src = p.read_text(encoding="utf-8")
        ast.parse(src)
        if _fires(src) and "register(" not in src and rel not in ALLOWLIST:
            bad.append(rel)
    assert bad == []


def test_scan_negative_control():
    assert _fires("self.bridge.dispatch(SetReviewer(n))")
    assert not _fires("self.go_to(stage)")
