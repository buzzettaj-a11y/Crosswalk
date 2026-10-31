"""Held controls and the run hold (SPEC 11.3). A held control stays focusable and says what releases it. It's never
setEnabled(False), so a screen reader still reaches it and reads the caption."""
from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QComboBox, QLineEdit, QWidget

from wholecount import copy
from wholecount.ui.widgets.style import button, label, set_prop, vbox


@dataclass(frozen=True)
class HoldReason:
    copy_id: str
    params: dict = field(default_factory=dict)

    @property
    def text(self):
        return copy.get(self.copy_id, **self.params)


RUN_HOLD = HoldReason("hold.run")
CAPTION_MIN_WIDTH = 220                   # a held caption never wraps to a sliver under a short button


class HeldAction(QWidget):
    clicked = Signal()

    def __init__(self, copy_id, kind="primary", params=None, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._holds = []
        self._run_held = False
        lay = vbox(self, spacing=4)
        self.button = button(copy.get(copy_id, **(params or {})), kind)
        self.caption = label("", role="caption", wrap=True)
        self.caption.setMinimumWidth(CAPTION_MIN_WIDTH)
        self.caption.setVisible(False)
        lay.addWidget(self.button)
        lay.addWidget(self.caption)
        self.button.clicked.connect(self._click)
        self._apply()

    def set_label(self, copy_id, **params):
        self.button.setText(copy.get(copy_id, **params))

    def set_kind(self, kind):
        self._kind = kind
        self._apply()

    def set_hold(self, reason):
        self.set_holds([reason] if reason else [])

    def set_holds(self, reasons):
        self._holds = [r for r in reasons if r]
        self._apply()

    def set_run_hold(self, on):
        self._run_held = bool(on)
        self._apply()

    @property
    def hold(self):
        """The run hold wins. Otherwise the first hold in the order the stage listed them."""
        if self._run_held:
            return RUN_HOLD
        return self._holds[0] if self._holds else None

    @property
    def held(self):
        return self.hold is not None

    def _apply(self):
        h = self.hold
        set_prop(self.button, "kind", "held" if h else self._kind)
        set_prop(self.button, "held", bool(h))
        self.caption.setText(h.text if h else "")
        self.caption.setVisible(h is not None)
        self.button.setAccessibleDescription(h.text if h else "")

    def _click(self):
        if not self.held:
            self.clicked.emit()


class _Swallow(QObject):
    """Swallows edits on a held checkbox, combo box or line edit. Tab and Shift+Tab still move focus."""

    PASS_KEYS = {Qt.Key_Tab, Qt.Key_Backtab}

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick, QEvent.Wheel):
            return True
        if t in (QEvent.KeyPress, QEvent.KeyRelease) and ev.key() not in self.PASS_KEYS:
            return True
        return False


class RunHold(QObject):
    """Every data-changing control registers here. While a job runs each is held; afterward each gets back the hold it
    had before, not simply unheld."""

    changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._filter = _Swallow(self)
        self._saved = {}
        self.active = False

    def register(self, widget, group="data"):
        self._prune()
        if widget not in self._items:
            self._items.append(widget)
            if self.active:
                self._hold_one(widget)
        return widget

    def _prune(self):
        """Stage bodies are rebuilt as the view changes; a control that no longer exists is let go."""
        from shiboken6 import isValid

        self._items = [w for w in self._items if isValid(w)]

    def registered(self):
        self._prune()
        return list(self._items)

    def _hold_one(self, w):
        if hasattr(w, "set_run_hold"):
            w.set_run_hold(True)
            return
        self._saved[id(w)] = (w.property("held"), w.accessibleDescription(),
                              w.isReadOnly() if isinstance(w, QLineEdit) else None)
        set_prop(w, "held", True)
        w.setAccessibleDescription(RUN_HOLD.text)
        if isinstance(w, QLineEdit):
            w.setReadOnly(True)
        else:
            w.installEventFilter(self._filter)

    def _release_one(self, w):
        if hasattr(w, "set_run_hold"):
            w.set_run_hold(False)
            return
        held, desc, ro = self._saved.pop(id(w), (None, "", None))
        set_prop(w, "held", held)
        w.setAccessibleDescription(desc)
        if isinstance(w, QLineEdit):
            w.setReadOnly(bool(ro))
        else:
            w.removeEventFilter(self._filter)

    def hold(self):
        if self.active:
            return
        self.active = True
        self._prune()
        for w in self._items:
            self._hold_one(w)
        self.changed.emit(True)

    def release(self):
        if not self.active:
            return
        self.active = False
        self._prune()
        for w in self._items:
            self._release_one(w)
        self.changed.emit(False)


HOLDABLE = (HeldAction, QAbstractButton, QCheckBox, QComboBox, QLineEdit)
