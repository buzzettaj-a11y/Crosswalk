"""DataLine: what the stage reads, changes and writes (SPEC 11.8). Every part is a claim with a test."""
from PySide6.QtWidgets import QFrame, QLabel

from wholecount import copy
from wholecount.ui.widgets.style import hbox, label

PARTS = ("reads", "changes", "writes")


def part_text(stage_id, part, saved_progress, data_notes=()):
    t = copy.get(f"dataline.{stage_id}.{part}")
    if part == "writes":
        if saved_progress and t.startswith("nothing to disk"):
            t += copy.get("dataline.saved_suffix")
        for note in data_notes:
            if note.startswith(f"dataline.note.{stage_id}."):
                t += " " + copy.get(note)
    return t


class DataLine(QFrame):
    def __init__(self, stage_id, saved_progress=True, data_notes=(), parent=None):
        super().__init__(parent)
        self.setObjectName("dataLine")
        self.stage_id = stage_id
        lay = hbox(self, (12, 8, 12, 8), 18)
        self.labels = {}
        for part in PARTS:
            box = hbox(spacing=6)
            box.addWidget(label(copy.get(f"dataline.label.{part}"), role="dl-label", name=f"dl_{part}_label"))
            v = label("", role="dl-text", wrap=True, name=f"dl_{part}")
            self.labels[part] = v
            box.addWidget(v, 1)
            lay.addLayout(box, 1)
        self.update_view(saved_progress, data_notes)

    def update_view(self, saved_progress, data_notes=()):
        for part, w in self.labels.items():
            w.setText(part_text(self.stage_id, part, saved_progress, data_notes))

    def text(self, part):
        return self.labels[part].text()
