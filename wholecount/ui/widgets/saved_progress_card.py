"""SavedProgressCard (closes A-19). The stage name comes from STAGES by the ID stored in the saved entry."""
from PySide6.QtWidgets import QFrame

from wholecount import copy
from wholecount.ui.frame.stages import BY_ID, STAGES
from wholecount.ui.widgets.style import label, set_prop, vbox


def card_lines(entry):
    """entry: dict with when (text), stage (a stage ID), files and decisions (ints)."""
    stage = BY_ID.get(entry.get("stage"), STAGES[0])
    return (copy.get("saved_card.when", when=entry["when"]), copy.get("saved_card.stage", stage=stage.plain),
            copy.get("saved_card.files", n=int(entry.get("files", 0))),
            copy.get("saved_card.decisions", k=int(entry.get("decisions", 0))))


class SavedProgressCard(QFrame):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        set_prop(self, "callout", "ink")
        lay = vbox(self, (14, 12, 14, 12), 4)
        when, stage, files, decisions = card_lines(entry)
        lay.addWidget(label(when, role="row-title"))
        lay.addWidget(label(stage, role="body"))
        lay.addWidget(label(f"{files} · {decisions}", role="note"))

    def text(self):
        from PySide6.QtWidgets import QLabel

        return " ".join(w.text() for w in self.findChildren(QLabel))
