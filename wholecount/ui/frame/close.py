"""Close Wholecount and Start over (SPEC 11.3, A-16).

Wholecount closes only when the operator closes it or the operating system ends it. There's no timer, no heartbeat and no
idle limit. The title bar's close and the Close button run the same code path.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from wholecount import copy
from wholecount.ui.widgets.style import button, hbox, label, vbox


def close_lines(has_batch, saved_progress, running):
    """The confirmation's sentences, or () when nothing is in memory and it closes at once."""
    if not has_batch and not running:
        return ()
    lines = [copy.get("close.confirm"), copy.get("close.saved_on" if saved_progress else "close.saved_off")]
    if running:
        lines.append(copy.get("close.running"))
    return tuple(lines)


def start_over_lines():
    return (copy.get("start.confirm"),)


class ConfirmDialog(QDialog):
    def __init__(self, title, lines, yes, no, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        lay = vbox(self, (24, 20, 24, 20), 10)
        lay.addWidget(label(title, role="h2"))
        self.lines = [label(t, role="body", wrap=True) for t in lines]
        for w in self.lines:
            lay.addWidget(w)
        row = hbox(spacing=8)
        self.yes = button(yes, "primary", name="confirmYes")
        self.no = button(no, "secondary", name="confirmNo")
        self.yes.clicked.connect(self.accept)
        self.no.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(self.no)
        row.addWidget(self.yes)
        lay.addLayout(row)
        self.setMinimumWidth(460)
        self.no.setFocus(Qt.OtherFocusReason)


def ask(parent, title, lines, yes, no):
    return ConfirmDialog(title, lines, yes, no, parent).exec() == QDialog.Accepted
