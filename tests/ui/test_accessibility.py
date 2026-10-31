"""Accessibility (SPEC 11.3, H14): 36px targets, names on text-less buttons, Tab order, and drawer focus traps."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QApplication, QComboBox, QLineEdit

from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount.ui.frame.stages import IDS


def _controls(w):
    """Visible controls a person tabs to. A spin box's own line edit is part of the spin box, which takes the focus."""
    from PySide6.QtWidgets import QAbstractSpinBox

    out = []
    for cls in (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox):
        out += [c for c in w.findChildren(cls) if c.isVisible()
                and not (isinstance(c, QLineEdit) and isinstance(c.parentWidget(), (QAbstractSpinBox, QComboBox)))]
    return out


@pytest.mark.parametrize("stage", IDS)
def test_targets_are_36px_and_named(make_window, stage):
    w = make_window(F.after_run(), stage=stage)
    for c in _controls(w):
        assert c.height() >= 36, (c.metaObject().className(), c.objectName(), c.height())
        if isinstance(c, QAbstractButton) and not c.text().strip():
            assert c.accessibleName(), c.objectName()
        assert c.focusPolicy() != Qt.NoFocus


@pytest.mark.parametrize("stage", IDS)
def test_tab_visits_every_control(make_window, qapp, stage):
    w = make_window(F.after_run(), stage=stage)
    w.activateWindow()
    w.strip.items["sources"].setFocus(Qt.TabFocusReason)
    seen = []
    for _ in range(120):
        fw = QApplication.focusWidget()
        if fw in seen:
            break
        seen.append(fw)
        w.focusNextChild()
        settle(qapp, 1)
    controls = set(_controls(w))
    assert controls <= set(seen), [c.objectName() or c.text() for c in controls - set(seen)]


def test_drawers_trap_tab_and_return_focus(make_window, qtbot, qapp):
    w = make_window(F.after_run())
    w.activateWindow()
    w.ledger.your_data.setFocus(Qt.TabFocusReason)
    w.ledger.your_data.click()
    settle(qapp)
    d = w.your_data
    for _ in range(12):
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
        assert d.panel.isAncestorOf(QApplication.focusWidget())
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key_Escape)
    settle(qapp)
    assert not d.isVisible()
    assert QApplication.focusWidget() is w.ledger.your_data


def test_help_button_is_named_and_stays_live(make_window, qtbot):
    from wholecount.ui.widgets.help import HelpButton

    w = make_window(F.after_run())
    b = HelpButton("el.ledger")
    qtbot.addWidget(b)
    assert b.text() == "?" and b.accessibleName() == "Help: The ledger" and b.height() >= 36 or b.minimumHeight() == 36
    w.run_hold.hold()
    assert b not in w.run_hold.registered()
    b.show()
    b.click()
    assert b._popover.isVisible()
    w.run_hold.release()
