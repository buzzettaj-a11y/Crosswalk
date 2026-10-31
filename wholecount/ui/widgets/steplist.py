"""StepList and StepRow (SPEC 11.6.1). Shared by the ticker's dropdown and, from M12, the Process panel."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QWidget

from wholecount import copy
from wholecount.session.progress import render
from wholecount.ui.theme import color
from wholecount.ui.widgets.style import hbox, label, vbox


class Bar(QWidget):
    """A track with a fill from the left. The width only grows while a job runs."""

    def __init__(self, height=4, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.fraction = 0.0
        self.done = False

    def set_fraction(self, f, done=False):
        self.fraction = max(self.fraction, max(0.0, min(1.0, f)))
        self.done = done
        self.update()

    def reset(self):
        self.fraction, self.done = 0.0, False
        self.update()

    def sizeHint(self):
        return QSize(120, self.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(color("line-soft")))
        w = int(self.width() * self.fraction)
        if w:
            p.fillRect(0, 0, w, self.height(), QColor(color("ink" if self.done else "blue-500")))
        p.end()


class StepRow(QFrame):
    def __init__(self, step_def, parent=None):
        super().__init__(parent)
        self.step_def = step_def
        lay = vbox(self, (0, 6, 0, 6), 4)
        top = hbox(spacing=8)
        self.name = label(copy.get(step_def.name_id), role="row-title", tone="muted")
        self.count = label(copy.get("steplist.waiting"), role="note")
        top.addWidget(self.name, 1)
        top.addWidget(self.count)
        lay.addLayout(top)
        self.bar = Bar(4)
        lay.addWidget(self.bar)
        self.message = label("", role="caption")
        lay.addWidget(self.message)

    def show_state(self, st):
        from wholecount.ui.widgets.style import set_prop

        if not st.begun:
            set_prop(self.name, "tone", "muted")
            self.count.setText(copy.get("steplist.waiting"))
            self.message.setText("")
            return
        set_prop(self.name, "tone", "ink")
        self.count.setText(copy.get("steplist.count", done=st.done, total=st.total))
        self.bar.set_fraction(st.fraction, st.ended)
        msg = st.found if st.ended and st.found is not None else st.message
        full = render(msg) if msg is not None else ""
        self.message.setToolTip(full)
        self.message.setText(self.message.fontMetrics().elidedText(full, Qt.ElideRight, max(80, self.width() - 4)))


class StepList(QFrame):
    def __init__(self, steps, parent=None):
        super().__init__(parent)
        lay = vbox(self, (0, 0, 0, 0), 2)
        self.rows = [StepRow(s) for s in steps]
        for r in self.rows:
            lay.addWidget(r)

    def show_model(self, model):
        for r, st in zip(self.rows, model.states):
            r.show_state(st)
