"""The run ticker and its dropdown (SPEC 11.6.1). Hidden until a job starts; it stays after the job until the next one.

The 2px bar along the bottom edge is the overall fraction and never moves backward. There's no animation beyond the bar
width, set directly, so reduced motion needs nothing special.
"""
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from wholecount import copy
from wholecount.session.progress import SourceRef, render
from wholecount.ui.theme import color
from wholecount.ui.widgets.source_mark import SourceMark
from wholecount.ui.widgets.steplist import StepList
from wholecount.ui.widgets.style import button, clear, hbox, label, vbox

HEIGHT = 34
DROPDOWN_WIDTH = 560


def source_of(message):
    if message is None:
        return None
    for v in message.params.values():
        if isinstance(v, SourceRef):
            return v
    return None


class RunTicker(QFrame):
    all_steps = Signal()
    cancel = Signal()
    show_log = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ticker")
        self.setFixedHeight(HEIGHT)
        lay = hbox(self, (20, 0, 20, 2), 10)
        self.left = label("", role="ticker", name="tickerLeft")
        self.mark_box = QWidget()
        mb = hbox(self.mark_box, spacing=0)
        self.mark_lay = mb
        self.message = label("", role="ticker-msg", name="tickerMessage")
        self.second = label("", role="ticker-msg", name="tickerSecond")
        lay.addWidget(self.left)
        lay.addWidget(self.mark_box)
        lay.addWidget(self.message, 1)
        lay.addWidget(self.second)
        self.all_button = button(copy.get("ticker.all_steps"), "quiet", "nav", name="tickerAll")
        self.cancel_button = button(copy.get("ticker.cancel"), "quiet", "lesser", name="tickerCancel")
        self.log_button = button(copy.get("ticker.show_log"), "quiet", "nav", name="tickerLog")
        for b in (self.all_button, self.cancel_button, self.log_button):
            lay.addWidget(b)
        self.all_button.clicked.connect(self.all_steps)
        self.cancel_button.clicked.connect(self.cancel)
        self.log_button.clicked.connect(self.show_log)
        self.fraction = 0.0
        self.mode = "idle"
        self.full_message = ""
        self.hide()

    def _set_mark(self, src):
        clear(self.mark_lay)
        if src is not None:
            self.mark_lay.addWidget(SourceMark(src.letter))
        self.mark_box.setVisible(src is not None)

    def set_fraction(self, f):
        self.fraction = max(self.fraction, min(1.0, f))
        self.update()

    def start(self):
        self.mode = "running"
        self.fraction = 0.0
        self.second.setText("")
        self.all_button.show()
        self.cancel_button.show()
        self.log_button.hide()
        self.left.setText("")
        self.message.setText("")
        self._set_mark(None)
        self.show()
        self.update()

    def show_progress(self, model):
        i = max(0, model.current)
        st = model.states[i]
        step = model.steps[i]
        self.left.setText(copy.get("ticker.running", i=i + 1, n=len(model.steps), step=copy.get(step.name_id),
                                   done=st.done, total=st.total))
        msg = st.message
        src = source_of(msg)
        self._set_mark(src)
        if msg is None:
            text = ""
        elif src is not None:
            # The mark stands for the letter, so the line shows the file name after it.
            text = render(msg).replace(f"[{src.letter}] ", "")
        else:
            text = render(msg)
        self.full_message = text
        self.message.setToolTip(text)
        self.message.setText(self.message.fontMetrics().elidedText(text, Qt.ElideRight, max(60, self.message.width())))
        self.set_fraction(model.overall_fraction())

    def finished(self, outcome, saved_progress):
        self.mode = "finished"
        self.fraction = 1.0
        secs = f"{outcome.seconds:.1f}"
        if outcome.action_id == "process":
            first = copy.get("ticker.after.process", secs=secs)
            second = copy.get("ticker.after.steps", n=outcome.steps) + ", " + copy.get("ticker.after.disk")
            if saved_progress:
                second += " " + copy.get("ticker.after.saved")
        else:
            first = copy.get("ticker.after.action", action=copy.get(f"action.{outcome.action_id}"), secs=secs)
            second = copy.get("ticker.after.steps", n=outcome.steps)
        self.left.setText(first)
        self._set_mark(None)
        self.message.setText("")
        self.second.setText(second)
        self.all_button.hide()
        self.cancel_button.hide()
        self.log_button.show()
        self.update()

    def cancelled(self):
        self.mode = "cancelled"
        self.left.setText(copy.get("ticker.cancelled"))
        self._set_mark(None)
        self.message.setText("")
        self.second.setText("")
        self.all_button.hide()
        self.cancel_button.hide()
        self.log_button.hide()
        self.update()

    def failed(self, step_name, code):
        self.mode = "failed"
        self.left.setText(copy.get("ticker.failed", step=step_name))
        self._set_mark(None)
        self.message.setText(copy.get("ticker.error_code", code=code))
        self.second.setText("")
        self.all_button.hide()
        self.cancel_button.hide()
        self.log_button.hide()
        self.update()

    def reset(self):
        self.mode = "idle"
        self.fraction = 0.0
        self.hide()

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if self.fraction > 0:
            p = QPainter(self)
            p.fillRect(0, self.height() - 2, int(self.width() * self.fraction), 2, QColor(color("blue-500")))
            p.end()


class LogView(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        lay = vbox(self, spacing=6)
        lay.addWidget(label(copy.get("ticker.log_title"), role="kicker"))
        self.lines = []
        for s, st in zip(model.steps, model.states):
            row = hbox(spacing=10)
            row.addWidget(label(copy.get(s.name_id), role="row-title"), 1)
            secs = label(copy.get("ticker.log_row", secs=f"{(st.seconds or 0):.1f}"), role="note")
            row.addWidget(secs)
            lay.addLayout(row)
            found = label(render(st.found) if st.found is not None else "", role="caption", wrap=True)
            lay.addWidget(found)
            self.lines.append((s, secs.text(), found.text()))


class Dropdown(QFrame):
    """A child of the central widget, raised over the content under the ticker, so it never pushes the layout."""

    closed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("dropdown")
        self.lay = vbox(self, (16, 12, 16, 14), 6)
        self.content = None
        self.hide()
        self._filter = _OutsideClick(self)

    def set_content(self, widget):
        clear(self.lay)
        self.content = widget
        self.lay.addWidget(widget)

    def open_at(self, x, y, by_keyboard=False):
        self.setFixedWidth(min(DROPDOWN_WIDTH, self.parentWidget().width() - 40))
        self.adjustSize()
        self.move(x, y)
        self.raise_()
        self.show()
        QApplication.instance().installEventFilter(self._filter)
        if by_keyboard:
            self.setFocus(Qt.TabFocusReason)

    def close_(self):
        if self.isVisible():
            self.hide()
            QApplication.instance().removeEventFilter(self._filter)
            self.closed.emit()


class _OutsideClick(QObject):
    def __init__(self, dropdown):
        super().__init__(dropdown)
        self.dd = dropdown

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Escape and self.dd.isVisible():
            self.dd.close_()
            return True
        if ev.type() == QEvent.MouseButtonPress and self.dd.isVisible() and isinstance(obj, QWidget):
            gp = ev.globalPosition().toPoint()
            if not self.dd.rect().contains(self.dd.mapFromGlobal(gp)):
                self.dd.close_()
        return False


def steplist_for(model):
    sl = StepList(model.steps)
    sl.show_model(model)
    return sl
