"""Pieces every stage body uses: cards, numbered section heads, source labels and plurals."""
from PySide6.QtWidgets import QFrame, QWidget

from wholecount import copy
from wholecount.ui.widgets.source_mark import SourceMark
from wholecount.ui.widgets.style import hbox, label, set_prop, vbox


class Card(QFrame):
    def __init__(self, kind="ink", rule=False, parent=None):
        super().__init__(parent)
        if rule:
            set_prop(self, "callout", kind)
        else:
            self.setObjectName("card")
        self.body = vbox(self, (18, 16, 18, 16), 10)


def card(kind="ink", rule=False):
    return Card(kind, rule)


def section_head(number, text, note=None, action=None):
    w = QWidget()
    lay = vbox(w, spacing=4)
    row = hbox(spacing=10)
    row.addWidget(label(f"{number}. {text}" if number else text, role="row-title"), 1)
    if action is not None:
        row.addWidget(action)
    lay.addLayout(row)
    if note:
        lay.addWidget(label(note, role="note", wrap=True))
    return w


def source_label(letter, name, role="row-title"):
    w = QWidget()
    lay = hbox(w, spacing=6)
    lay.addWidget(SourceMark(letter or "?"))
    lay.addWidget(label(name, role=role))
    lay.addStretch(1)
    return w


def pluralize(copy_id, n, **params):
    """copy_id.one when n is 1, else copy_id.many. Both take n."""
    return copy.get(f"{copy_id}.{'one' if n == 1 else 'many'}", n=n, **params)
