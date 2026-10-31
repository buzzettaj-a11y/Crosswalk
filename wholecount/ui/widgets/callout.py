"""Callouts: a white card with a 3px top rule in blue-500, green-500, amber-500 or ink (style guide)."""
from PySide6.QtWidgets import QFrame

from wholecount.ui.widgets.style import set_prop, vbox


class Callout(QFrame):
    def __init__(self, kind="needs", parent=None):
        super().__init__(parent)
        set_prop(self, "callout", kind)
        self.body = vbox(self, (16, 14, 16, 14), 8)
