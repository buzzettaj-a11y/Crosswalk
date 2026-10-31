"""The stage strip (SPEC 11.3, 10.4): nine StageItems and the Undo item. It never scrolls.

Each item paints its own 3px bottom rule, because QSS can't draw a partial fill. While a job runs, a stage that owns
running steps paints a track with a blue fill from the left.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QPushButton, QSizePolicy

from wholecount import copy
from wholecount.ui.frame.captions import CURRENT, DONE, NOTHING, stage_caption, stage_state
from wholecount.ui.frame.stages import STAGES, strip_kicker
from wholecount.ui.theme import color
from wholecount.ui.widgets.style import hbox, label, set_prop, vbox

HEIGHT = 64
UNDO_WIDTH, UNDO_WIDTH_COMPACT = 176, 150
RULE = 3


def _ignore_mouse(*ws):
    for w in ws:
        w.setAttribute(Qt.WA_TransparentForMouseEvents)


class StageItem(QPushButton):
    def __init__(self, stage, parent=None):
        super().__init__(parent)
        self.stage = stage
        set_prop(self, "strip", "item")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumHeight(HEIGHT)
        lay = vbox(self, (10, 8, 8, 8), 2)
        self.kicker = label(strip_kicker(stage.id), role="strip-kicker")
        self.name = label(stage.plain, role="stage-name", wrap=True)
        self.caption = label("", role="strip-caption")
        _ignore_mouse(self.kicker, self.name, self.caption)
        for w in (self.kicker, self.name, self.caption):
            lay.addWidget(w)
        lay.addStretch(1)
        self.state = None
        self.stale = False
        self.full_caption = ""
        self.run_fraction = None

    def show_view(self, view, current, compact=False):
        st = stage_state(self.stage.id, view, current)
        cap = stage_caption(self.stage.id, view)
        self.state, self.stale = st, cap.stale
        set_prop(self, "state", st)
        set_prop(self, "stale", cap.stale)
        set_prop(self.name, "tone", "blue" if st == CURRENT else ("muted" if st == "later" else "ink"))
        f = self.name.font()
        f.setPixelSize(11 if compact else 12)
        self.name.setFont(f)
        self.full_caption = cap.text
        tone = "amber" if cap.stale else ("blue" if st == CURRENT else cap.parts[0][2] or "muted")
        if not cap.stale and len(cap.parts) > 1 and cap.parts[-1][2]:
            tone = cap.parts[-1][2] if st != CURRENT else "blue"
        set_prop(self.caption, "tone", tone)
        self.caption.setToolTip(self.full_caption)
        self.setToolTip(self.full_caption)
        self._elide()
        name = copy.get("stage.accessible", number=self.stage.nn, name=self.stage.plain, caption=self.full_caption)
        if st == CURRENT:
            name += copy.get("stage.accessible_current")
        if cap.stale:
            name += copy.get("stage.accessible_stale")
        self.setAccessibleName(name)
        self.setAccessibleDescription(self.full_caption)
        self.update()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._elide()

    def _elide(self):
        w = max(20, self.width() - 18)
        self.caption.setText(self.caption.fontMetrics().elidedText(self.full_caption, Qt.ElideRight, w))

    def set_run_fraction(self, f):
        self.run_fraction = f
        self.update()

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        y = self.height() - RULE
        if self.run_fraction is not None:
            p.fillRect(0, y, self.width(), RULE, QColor(color("line-soft")))
            p.fillRect(0, y, int(self.width() * self.run_fraction), RULE, QColor(color("blue-500")))
        else:
            rule = {CURRENT: "blue-500", DONE: "ink", NOTHING: "line-2"}.get(self.state)
            if rule:
                p.fillRect(0, y, self.width(), RULE, QColor(color(rule)))
        p.end()


class UndoItem(QPushButton):
    def __init__(self, on_undo, parent=None):
        super().__init__(parent)
        set_prop(self, "strip", "item")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(UNDO_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setMinimumHeight(HEIGHT)
        lay = vbox(self, (12, 8, 8, 8), 2)
        self.kicker = label(copy.get("strip.undo.kicker"), role="strip-kicker")
        self.label_ = label("", role="stage-name", tone="blue")
        self.caption = label(copy.get("strip.undo.caption"), role="strip-caption")
        self.hold_caption = label("", role="strip-caption", tone="muted")
        _ignore_mouse(self.kicker, self.label_, self.caption, self.hold_caption)
        for w in (self.kicker, self.label_, self.caption, self.hold_caption):
            lay.addWidget(w)
        lay.addStretch(1)
        self.hold_caption.hide()
        self.full_label = ""
        self.empty = True
        self.run_held = False
        self.clicked.connect(self._click)
        self._on_undo = on_undo

    @property
    def held(self):
        return self.empty or self.run_held

    def set_compact(self, compact):
        self.setFixedWidth(UNDO_WIDTH_COMPACT if compact else UNDO_WIDTH)
        self._elide()

    def show_view(self, view):
        self.empty = view.undo_label is None
        if self.empty:
            self.full_label = copy.get("strip.undo.empty")
        else:
            key, params = view.undo_label
            self.full_label = copy.get(key, **params)
        self._apply()

    def set_run_hold(self, on):
        self.run_held = bool(on)
        self._apply()

    def _apply(self):
        from wholecount.ui.widgets.held import RUN_HOLD

        set_prop(self.label_, "tone", "muted" if self.held else "blue")
        set_prop(self, "held", self.held)
        self.setToolTip(self.full_label)
        self.setAccessibleName(copy.get("strip.undo.accessible", label=self.full_label))
        desc = RUN_HOLD.text if self.run_held else copy.get("strip.undo.caption")
        self.setAccessibleDescription(desc)
        self.hold_caption.setVisible(False)
        self._elide()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._elide()

    def _elide(self):
        self.label_.setText(self.label_.fontMetrics().elidedText(self.full_label, Qt.ElideRight, max(20, self.width() - 20)))

    def _click(self):
        if not self.held:
            self._on_undo()

    def paintEvent(self, ev):
        super().paintEvent(ev)


class StageStrip(QFrame):
    go = Signal(str)

    def __init__(self, on_undo, parent=None):
        super().__init__(parent)
        self.setObjectName("strip")
        lay = hbox(self, spacing=0)
        self.items = {}
        for s in STAGES:
            it = StageItem(s)
            it.clicked.connect(lambda _=False, sid=s.id: self.go.emit(sid))
            self.items[s.id] = it
            lay.addWidget(it, 1)
        div = QFrame()
        div.setObjectName("rule")
        div.setFixedWidth(1)
        div.setMinimumHeight(HEIGHT)
        div.setMaximumHeight(16777215)
        lay.addWidget(div)
        self.undo = UndoItem(on_undo)
        lay.addWidget(self.undo)
        self.compact = False
        self.setMinimumHeight(HEIGHT)

    def set_compact(self, compact):
        self.compact = compact
        self.undo.set_compact(compact)

    def update_view(self, view, current):
        for it in self.items.values():
            it.show_view(view, current, self.compact)
        self.undo.show_view(view)
        self.updateGeometry()

    def set_run_fractions(self, fractions):
        """fractions: stage ID -> fraction, or None to go back to the state colors."""
        for sid, it in self.items.items():
            it.set_run_fraction(None if fractions is None else fractions.get(sid))

    def sizeHint(self):
        h = max(HEIGHT, max(it.sizeHint().height() for it in self.items.values()))
        return QSize(super().sizeHint().width(), h)
