"""Labeling one pair (SPEC 8.8, M13 CAL-2). Two records side by side and three buttons, Same, Different and Unsure, with the
keys S, D and U. The labeler never sees the score, band or evidence, so the number can't lead them. Values come from memory
and are never written."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLineEdit, QProgressBar, QWidget

from wholecount import copy
from wholecount.session import calibration as cs
from wholecount.ui.widgets.style import button, hbox, label, vbox

KEYS = {Qt.Key_S: "same", Qt.Key_D: "different", Qt.Key_U: "unsure"}


class LabelView(QWidget):
    done = Signal()                 # both labelers finished

    def __init__(self, window, cal):
        super().__init__()
        self.window_ = window
        self.cal = cal
        self.who = None
        self.i = 0
        self.setFocusPolicy(Qt.StrongFocus)
        lay = vbox(self, spacing=10)
        lay.addWidget(label(copy.get("matching.label.no_score"), role="note", wrap=True, name="labelNoScore"))
        name_row = hbox(spacing=8)
        self.name = QLineEdit()
        self.name.setObjectName("labelerName")
        self.name.setPlaceholderText(copy.get("matching.label.name"))
        self.start_button = button(copy.get("matching.label.start"), "primary", name="labelStart")
        self.start_button.clicked.connect(lambda: self.start(self.name.text()))
        name_row.addWidget(self.name, 1)
        name_row.addWidget(self.start_button)
        lay.addLayout(name_row)
        self.message = label("", role="note", tone="amber", wrap=True, name="labelMessage")
        lay.addWidget(self.message)
        self.grid = QGridLayout()
        lay.addLayout(self.grid)
        buttons = hbox(spacing=8)
        self.choice = {}
        for value in ("same", "different", "unsure"):
            b = button(copy.get(f"matching.label.{value}"), "primary" if value == "same" else "secondary",
                       name=f"label_{value}")
            b.clicked.connect(lambda _=False, v=value: self.choose(v))
            self.choice[value] = b
            buttons.addWidget(b)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        self.bar = QProgressBar()
        self.bar.setObjectName("labelProgress")
        self.bar.setTextVisible(False)
        lay.addWidget(self.bar)
        self.progress = label("", role="caption", name="labelProgressText")
        lay.addWidget(self.progress)
        self.handover = button(copy.get("matching.label.handover"), "secondary", name="labelHandover")
        self.handover.clicked.connect(self.hand_over)
        lay.addWidget(self.handover, 0, Qt.AlignLeft)
        self.second_note = label(copy.get("matching.label.second"), role="caption", wrap=True)
        lay.addWidget(self.second_note)
        lay.addStretch(1)
        self._show(False)

    def _show(self, labeling):
        for b in self.choice.values():
            b.setEnabled(labeling)
        self.handover.setVisible(labeling and self.i >= len(self.cal.pairs))
        self.second_note.setVisible(bool(self.cal.labelers) and not labeling)

    def start(self, name):
        try:
            self.cal.start(name)
        except cs.CalibrationRefused as e:
            self.message.setText(copy.get(f"calibration.refused.{e.code}"))
            return False
        self.message.setText("")
        self.who = name.strip()
        mine = self.cal.labels_for(self.who)
        self.i = next((k for k, p in enumerate(self.cal.pairs) if p.pair_id not in mine), len(self.cal.pairs))
        self._draw()
        self._show(True)
        self.setFocus()
        return True

    def _draw(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        total = len(self.cal.pairs)
        self.bar.setRange(0, max(total, 1))
        self.bar.setValue(self.i)
        self.progress.setText(copy.get("matching.label.progress", done=self.i, total=total, name=self.who or ""))
        if self.i >= total:
            self._show(True)
            return
        p = self.cal.pairs[self.i]
        s = self.window_.bridge.session
        for row, f in enumerate(cs.FIELDS):
            self.grid.addWidget(label(copy.get(f"matching.field.{f}"), role="caption"), row, 0)
        for col, pk in enumerate((p.a, p.b), start=1):
            rec = cs.side(s, pk)
            for row, f in enumerate(cs.FIELDS):
                text = rec[f] or copy.get("matching.field.blank")
                self.grid.addWidget(label(text, role="row-title" if f == "name" else "note", name=f"rec{col - 1}_{f}"), row,
                                    col)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)

    def choose(self, value):
        if self.who is None or self.i >= len(self.cal.pairs):
            return False
        self.cal.label(self.who, self.cal.pairs[self.i].pair_id, value)
        self.i += 1
        self._draw()
        return True

    def keyPressEvent(self, ev):
        if ev.key() in KEYS and not self.name.hasFocus():
            self.choose(KEYS[ev.key()])
            return
        super().keyPressEvent(ev)

    def hand_over(self):
        if self.who is None:
            return
        self.cal.finish(self.who)
        self.who = None
        self.i = 0
        self.name.clear()
        self._draw()
        self._show(False)
        if self.cal.both_finished():
            self.done.emit()
