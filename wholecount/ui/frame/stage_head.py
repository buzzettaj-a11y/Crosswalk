"""StageHead: the one function that builds every stage header, empty states included (A-21)."""
from PySide6.QtWidgets import QWidget

from wholecount import copy
from wholecount.ui.frame.stages import BY_ID, kicker
from wholecount.ui.widgets.dataline import DataLine
from wholecount.ui.widgets.style import hbox, label, vbox


class StageHead(QWidget):
    def __init__(self, stage_id, actions=(), empty=False, saved_progress=True, data_notes=(), parent=None):
        super().__init__(parent)
        self.stage_id = stage_id
        self.empty = empty
        lay = vbox(self, spacing=8)
        row = hbox(spacing=16)
        left = vbox(spacing=4)
        self.kicker = label(kicker(stage_id), role="kicker", name="stageKicker")
        self.title = label(BY_ID[stage_id].plain, role="h2", name="stageTitle")
        self.subtitle = label(copy.get(BY_ID[stage_id].subtitle_id), role="body", tone="muted", wrap=True)
        left.addWidget(self.kicker)
        left.addWidget(self.title)
        left.addWidget(self.subtitle)
        row.addLayout(left, 1)
        self.actions = list(actions)
        for a in self.actions:
            row.addWidget(a)
        lay.addLayout(row)
        self.dataline = DataLine(stage_id, saved_progress, data_notes)
        lay.addWidget(self.dataline)
