"""HelpButton(help_id) and its popover (SPEC 11.9). Keys are help.stage.<stage> and help.el.<element>, each with title,
purpose and how. Help stays live during a run, so it never registers with the run hold."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame

from wholecount import copy
from wholecount.ui.widgets.style import button, label, set_prop, vbox


class HelpPopover(QFrame):
    def __init__(self, help_id, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("popover")
        lay = vbox(self, (14, 12, 14, 12), 6)
        lay.addWidget(label(copy.get(f"help.{help_id}.title"), role="row-title"))
        lay.addWidget(label(copy.get(f"help.{help_id}.purpose"), role="note", tone="ink-2", wrap=True))
        lay.addWidget(label(copy.get(f"help.{help_id}.how"), role="note", tone="ink-2", wrap=True))
        self.setFixedWidth(320)


class HelpButton:
    """A 36px quiet button with the text ? and the accessible name Help: {title}."""

    def __new__(cls, help_id, parent=None):
        b = button(copy.get("help.button"), "quiet", "nav")
        b.setParent(parent)
        b.setFixedSize(36, 36)
        b.setAccessibleName(copy.get("help.accessible", title=copy.get(f"help.{help_id}.title")))
        b.setProperty("help_id", help_id)
        set_prop(b, "live", True)

        def open_():
            pop = HelpPopover(help_id, b)
            pop.move(b.mapToGlobal(b.rect().bottomLeft()))
            pop.show()
            b._popover = pop
        b.clicked.connect(open_)
        return b
