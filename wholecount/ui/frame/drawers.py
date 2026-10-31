"""Drawers (SPEC 11.3, 11.8): Details, Your data, System check and Settings.

A drawer is an overlay child of the central widget with an ink scrim at 35 percent, drawn in paintEvent. That scrim is the
one place alpha is used. Escape, the scrim and Close shut it. Focus moves in on open, Tab stays inside, and focus returns
to the opener on close.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import QCheckBox, QFrame, QGridLayout, QWidget

from wholecount import brand, copy
from wholecount.ui.theme import color
from wholecount.ui.widgets.style import WrapScroll, button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tag import tag

SCRIM_ALPHA = 0.35
STATUS_TAG = {"ok": "confirmed", "warn": "wrong", "missing": "neutral"}


class Drawer(QWidget):
    closed = Signal()

    def __init__(self, parent, side="right", width=520, kicker_key=None, title_key=None):
        super().__init__(parent)
        self.side = side
        self.max_width = width
        self.panel = QFrame(self)
        self.panel.setObjectName("drawer")
        outer = vbox(self.panel)
        top = hbox(spacing=8)
        top.setContentsMargins(24, 16, 16, 0)
        heads = vbox(spacing=4)
        if kicker_key:
            heads.addWidget(label(copy.get(kicker_key).upper(), role="kicker"))
        if title_key:
            heads.addWidget(label(copy.get(title_key), role="drawer-title"))
        top.addLayout(heads, 1)
        self.close_button = button(copy.get("drawer.close"), "quiet", "nav", name="drawerClose")
        self.close_button.clicked.connect(self.close_)
        top.addWidget(self.close_button, 0, Qt.AlignTop)
        outer.addLayout(top)
        self.scroll = WrapScroll()
        self.inner = QWidget()
        self.body = vbox(self.inner, (24, 12, 24, 24), 14)
        self.scroll.setWidget(self.inner)
        outer.addWidget(self.scroll, 1)
        self._opener = None
        self.hide()

    def relayout(self):
        p = self.parentWidget()
        self.setGeometry(0, 0, p.width(), p.height())
        w = min(self.max_width, p.width())
        self.panel.setGeometry(0 if self.side == "left" else p.width() - w, 0, w, p.height())
        self.scroll.fit()

    def open_(self):
        self._opener = self.window().focusWidget() if self.window() else None
        self.relayout()
        self.show()
        self.raise_()
        first = self._focusables()
        (first[0] if first else self.close_button).setFocus(Qt.TabFocusReason)

    def close_(self):
        if not self.isVisible():
            return
        self.hide()
        if self._opener is not None:
            try:
                self._opener.setFocus(Qt.OtherFocusReason)
            except RuntimeError:
                pass
        self.closed.emit()

    def _focusables(self):
        out = []
        for w in self.panel.findChildren(QWidget):
            if w.isVisibleTo(self.panel) and w.focusPolicy() & Qt.TabFocus and w.isEnabled():
                out.append(w)
        return out

    def focusNextPrevChild(self, nxt):
        ws = self._focusables()
        if not ws:
            return True
        cur = self.window().focusWidget()
        i = ws.index(cur) if cur in ws else -1
        ws[(i + (1 if nxt else -1)) % len(ws)].setFocus(Qt.TabFocusReason if nxt else Qt.BacktabFocusReason)
        return True

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.close_()
            return
        super().keyPressEvent(ev)

    def mousePressEvent(self, ev):
        if not self.panel.geometry().contains(ev.position().toPoint()):
            self.close_()
            return
        super().mousePressEvent(ev)

    def paintEvent(self, _):
        p = QPainter(self)
        scrim = QColor(color("ink"))
        scrim.setAlphaF(SCRIM_ALPHA)
        p.fillRect(self.rect(), scrim)
        p.end()


class DetailsDrawer(Drawer):
    """Holds the one LedgerPanel. The panel scrolls itself, so the drawer's own scroll area stays empty and hidden."""

    def __init__(self, parent):
        super().__init__(parent, "left", 320)
        self.scroll.hide()
        self.slot = vbox(margins=(20, 8, 20, 0))
        self.panel.layout().addLayout(self.slot, 1)

    def hold(self, panel):
        clear(self.slot)
        self.slot.addWidget(panel)
        panel.show()


class SavedSwitch(QWidget):
    """The saved-progress switch: a checkbox styled as a switch with a 36px target. One setting, two places."""

    toggled_by_user = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = vbox(self, spacing=4)
        self.check = QCheckBox(copy.get("data.saved.switch"))
        set_prop(self.check, "switch", True)
        self.check.setMinimumHeight(36)
        self.check.toggled.connect(self.toggled_by_user)
        self.state = label("", role="note", name="savedState")
        self.last = label("", role="caption", name="savedLast")
        lay.addWidget(self.check)
        lay.addWidget(self.state)
        lay.addWidget(self.last)

    def update_view(self, v):
        from wholecount.ui.frame.topbar import saved_text

        self.check.blockSignals(True)
        self.check.setChecked(v.saved_progress)
        self.check.blockSignals(False)
        self.state.setText(copy.get("data.saved.on" if v.saved_progress else "data.saved.off"))
        has = v.saved_progress and v.saved_at is not None
        self.last.setVisible(has)
        if has:
            when = saved_text(v, v.now).replace("progress saved ", "")
            self.last.setText(copy.get("data.saved.last", when=when))


def _box(title_key, text_key, strong=False):
    f = QFrame()
    f.setObjectName("flowBoxMemory" if strong else "flowBox")
    lay = vbox(f, (14, 12, 14, 12), 4)
    lay.addWidget(label(copy.get(title_key), role="box-title"))
    lay.addWidget(label(copy.get(text_key), role="note", tone="ink-2", wrap=True))
    return f


def _arrow(key):
    return label(copy.get(key), role="caption", tone="muted")


NEVER_LINES = ("data.never.internet", "data.never.ai", "data.never.log", "data.never.kept")


class YourDataDrawer(Drawer):
    saved_toggled = Signal(bool)
    open_guide = Signal()

    def __init__(self, parent):
        super().__init__(parent, "right", 520, "data.kicker", "data.title")
        b = self.body
        self.boxes = [_box("data.box.files.title", "data.box.files.body"), _arrow("data.arrow.read"),
                      _box("data.box.memory.title", "data.box.memory.body", strong=True), _arrow("data.arrow.download"),
                      _box("data.box.out.title", "data.box.out.body")]
        for w in self.boxes:
            b.addWidget(w)
        b.addWidget(label(copy.get("data.saved.title"), role="row-title"))
        b.addWidget(label(copy.get("data.saved.body"), role="note", tone="ink-2", wrap=True))
        self.switch = SavedSwitch()
        self.switch.toggled_by_user.connect(self.saved_toggled)
        b.addWidget(self.switch)
        self.notes = vbox(spacing=6)
        b.addLayout(self.notes)
        never = QFrame()
        never.setObjectName("never")
        nl = vbox(never, (14, 12, 14, 12), 6)
        nl.addWidget(label(copy.get("data.never.title").upper(), role="kicker"))
        self.never_lines = []
        for k in NEVER_LINES:
            w = label(copy.get(k), role="note", tone="ink-2", wrap=True)
            self.never_lines.append(w)
            nl.addWidget(w)
        b.addWidget(never)
        # M15: a quiet link at the bottom opens the user guide.
        self.guide_link = button(copy.get("guide.open"), "quiet", "nav", name="openGuide")
        self.guide_link.clicked.connect(self.open_guide)
        b.addWidget(self.guide_link, 0, Qt.AlignLeft)
        b.addStretch(1)

    def update_view(self, v):
        self.switch.update_view(v)
        clear(self.notes)
        for note in (n for n in v.data_notes if not n.startswith("dataline.")):
            self.notes.addWidget(label(copy.get(note), role="note", tone="ink-2", wrap=True, name="dataNote"))

    def texts(self):
        from PySide6.QtWidgets import QLabel

        return [w.text() for w in self.inner.findChildren(QLabel)]


class CheckTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(8)
        self.rows = []

    def update_view(self, v):
        clear(self.grid)
        for i, k in enumerate(("check.col.check", "check.col.status", "check.col.detail")):
            self.grid.addWidget(label(copy.get(k), role="column-head"), 0, i)
        self.rows = []
        for r, row in enumerate(v.checks, start=1):
            name = copy.get(f"check.row.{row.check_id}")
            status = copy.get(f"check.status.{row.status}")
            key, params = row.detail
            detail = copy.get(key, **params)
            self.grid.addWidget(label(name, role="note", tone="ink"), r, 0)
            self.grid.addWidget(tag(status, STATUS_TAG[row.status]), r, 1, Qt.AlignLeft)
            d = label(detail, role="note", tone="amber" if row.status == "warn" else "ink-2", wrap=True)
            self.grid.addWidget(d, r, 2)
            self.rows.append((row.check_id, status, detail, row.status))
        self.grid.setColumnStretch(2, 1)


def support_report(view):
    """Version and set-up only (H8). Built from the same rows as the table."""
    lines = [copy.get("app.version_line", version=brand.VERSION)]
    for row in view.checks:
        key, params = row.detail
        lines.append(copy.get("check.support.line", check=copy.get(f"check.row.{row.check_id}"),
                              status=copy.get(f"check.status.{row.status}"), detail=copy.get(key, **params)))
    return "\n".join(lines)


class SystemCheckDrawer(Drawer):
    def __init__(self, parent):
        super().__init__(parent, "right", 560, "check.kicker", "check.title")
        self.table = CheckTable()
        self.body.addWidget(self.table)
        box = QFrame()
        box.setObjectName("never")
        bl = vbox(box, (14, 12, 14, 12), 6)
        bl.addWidget(label(copy.get("check.support.title"), role="row-title"))
        bl.addWidget(label(copy.get("check.support.body"), role="note", tone="ink-2", wrap=True))
        self.copy_button = button(copy.get("check.support.copy"), "secondary", name="copyReport")
        self.copy_button.clicked.connect(self.copy_report)
        bl.addWidget(self.copy_button, 0, Qt.AlignLeft)
        self.body.addWidget(box)
        self.body.addStretch(1)
        self.view = None

    def update_view(self, v):
        self.view = v
        self.table.update_view(v)

    def copy_report(self):
        text = support_report(self.view)
        QGuiApplication.clipboard().setText(text)
        return text


class SettingsDrawer(Drawer):
    saved_toggled = Signal(bool)
    change_reviewer = Signal()

    def __init__(self, parent):
        super().__init__(parent, "right", 560, "settings.kicker", "settings.title")
        b = self.body
        b.addWidget(label(copy.get("settings.saved"), role="row-title"))
        self.switch = SavedSwitch()
        self.switch.toggled_by_user.connect(self.saved_toggled)
        b.addWidget(self.switch)
        b.addWidget(label(copy.get("settings.reviewer"), role="row-title"))
        rv = hbox(spacing=8)
        self.reviewer = label("", role="note", name="settingsReviewer")
        self.change = button(copy.get("ledger.foot.change"), "quiet", "nav", name="settingsReviewerChange")
        self.change.clicked.connect(self.change_reviewer)
        rv.addWidget(self.reviewer, 1)
        rv.addWidget(self.change)
        b.addLayout(rv)
        b.addWidget(label(copy.get("settings.reviewer_default"), role="caption", wrap=True))
        b.addWidget(label(copy.get("settings.check"), role="row-title"))
        self.table = CheckTable()
        b.addWidget(self.table)
        self.sections = vbox(spacing=14)       # M13 adds its sections here
        b.addLayout(self.sections)
        b.addStretch(1)

    def update_view(self, v):
        self.switch.update_view(v)
        self.reviewer.setText(copy.get("ledger.foot.reviewer", name=v.reviewer) if v.reviewer
                              else copy.get("ledger.foot.reviewer_none"))
        self.table.update_view(v)
