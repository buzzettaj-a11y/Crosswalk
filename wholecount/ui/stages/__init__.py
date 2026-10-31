"""StageRegistry: build(stage_id) -> QWidget. M10 registers placeholders; M11 and M12 register the real bodies."""
from PySide6.QtWidgets import QWidget

from wholecount import copy
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import label, vbox


def placeholder(stage_id, window):
    view = window.view
    w = QWidget()
    lay = vbox(w, spacing=16)
    actions = []
    if stage_id == "run":
        act = HeldAction("action.process", "primary")
        act.setObjectName("processAction")
        act.clicked.connect(window.on_process)
        window.run_hold.register(act)
        actions.append(act)
    head = StageHead(stage_id, actions, saved_progress=view.saved_progress, data_notes=view.data_notes)
    lay.addWidget(head)
    lay.addWidget(label(copy.get("stage.placeholder"), role="note", wrap=True, name="placeholderNote"))
    lay.addStretch(1)
    w.head = head
    return w


def _real_builders():
    from wholecount.ui.stages import map as map_
    from wholecount.ui.stages import export, prepare, programs, review, run, schema, sources, summary

    return {"sources": sources.build, "schema": schema.build, "prepare": prepare.build, "map": map_.build,
            "programs": programs.build, "run": run.build, "review": review.build,
            "summary": summary.build, "export": export.build}


class StageRegistry:
    def __init__(self, builders=None):
        self.builders = dict(_real_builders() if builders is None else builders)

    def register(self, stage_id, builder):
        self.builders[stage_id] = builder

    def build(self, stage_id, window):
        return self.builders.get(stage_id, placeholder)(stage_id, window)
