"""Stage sections for the ledger (SPEC 11.3, section 8a of M10): Tidy up, Match your columns and Programs.
Each reads FrameView only. Showing one belongs to the stage that's open."""
from PySide6.QtWidgets import QWidget

from wholecount import copy
from wholecount.ui.widgets.style import clear, hbox, label, rule, vbox


class _StageSection(QWidget):
    stage_id = ""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        outer = vbox(self, spacing=10)
        outer.addWidget(rule())
        outer.addWidget(label(copy.get(f"stage.{self.stage_id}.name").upper(), role="ledger-kicker"))
        self.body = vbox(spacing=6)
        outer.addLayout(self.body)
        self.update_view(view)

    def row(self, key, value, tone=None, **params):
        box = hbox(spacing=8)
        box.addWidget(label(copy.get(key, **params), role="note", tone=tone or "ink"), 1)
        box.addWidget(label(value if isinstance(value, str) else f"{value:,}", role="row-title", tone=tone or "ink"))
        self.body.addLayout(box)

    def update_view(self, v):
        clear(self.body)
        self.fill(v)


class PrepareSection(_StageSection):
    stage_id = "prepare"

    def fill(self, v):
        self.row("ledger.section.prepare.proposed", v.steps_proposed)
        self.row("ledger.section.prepare.added", v.steps_added, "green")
        self.row("ledger.section.prepare.removed", v.steps_removed)
        self.row("ledger.section.prepare.noop", v.steps_noop, "amber")
        self.body.addWidget(label(copy.get("ledger.section.prepare.note"), role="caption", wrap=True))


class MapSection(_StageSection):
    stage_id = "map"

    def fill(self, v):
        self.row("ledger.section.map.confirmed", copy.get("ledger.section.map.of", m=v.map_confirmed, t=v.map_tables))
        s, t = v.map_required
        self.row("ledger.section.map.required", copy.get("ledger.section.map.of", m=s, t=t))
        self.row("ledger.section.map.wrong", v.map_wrong, "blue")


class ProgramsSection(_StageSection):
    stage_id = "programs"

    def fill(self, v):
        self.row("ledger.section.programs.files", v.program_files)
        self.row("ledger.section.programs.names", v.program_names)
        self.row("ledger.section.programs.counted", v.programs_counted)
        self.row("ledger.section.programs.open", v.program_groups_open, "blue")
        self.row("ledger.section.programs.confirmed", v.program_groups_confirmed)
        p = v.preview
        if p is not None:
            self.row("ledger.counts.goal1", p.goal1)
            self.row("ledger.counts.goal2", p.goal2)
            self.body.addWidget(label(copy.get("ledger.section.programs.preview"), role="caption"))
            if p.stale:
                self.body.addWidget(label(copy.get("ledger.section.programs.preview_stale", time=p.taken_at),
                                          role="caption", tone="amber", wrap=True))


SECTIONS = {"prepare": PrepareSection, "map": MapSection, "programs": ProgramsSection}
