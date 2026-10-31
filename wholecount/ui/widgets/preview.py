"""DataPreview (M11 section 0): a table's first rows in a 720px drawer from the right, with the header row picker.
Values show on screen only. Picking a row fires a set-up change for that table's header row; none numbers the columns."""
from PySide6.QtWidgets import QButtonGroup, QRadioButton, QWidget

from wholecount import copy
from wholecount.session.commands import SetupChange
from wholecount.ui.frame.drawers import Drawer
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.grid import grid_with_pager
from wholecount.ui.widgets.style import clear, label, vbox

PICK_ROWS = 8


class DataPreview(Drawer):
    def __init__(self, parent, window):
        super().__init__(parent, "right", 720, "preview.kicker", None)
        self.window_ = window
        self.content = vbox()
        self.body.addLayout(self.content)
        self.body.addStretch(1)
        self.table_key = None
        self.radios = []

    def show_table(self, table_key):
        self.table_key = table_key
        clear(self.content)
        sv = self.window_.bridge.survey()
        if sv is None:
            return
        facts = sv.table(table_key)
        t = next(x for x in self.window_.bridge.loaded_tables() if x.key == table_key)
        self.content.addWidget(label(copy.get("preview.title", name=facts.file_name), role="drawer-title"))
        if facts.header_warning:
            c = Callout("wrong")
            c.body.addWidget(label(copy.get("preview.header_wrong"), role="row-title", tone="amber"))
            c.body.addWidget(label(copy.get(f"preview.header_reason.{facts.header_warning}"), role="note", wrap=True))
            self.content.addWidget(c)
        self.content.addWidget(label(copy.get("preview.pick"), role="row-title"))
        picker = QWidget()
        pl = vbox(picker, spacing=0)
        self.group = QButtonGroup(picker)
        self.radios = []
        none = QRadioButton(copy.get("preview.none"))
        none.setChecked(facts.header_is_virtual or facts.header_row == 0)
        self.group.addButton(none, 0)
        pl.addWidget(none)
        self.radios.append(none)
        first_block = [s for s in t.source_rows if s.block == 0][:PICK_ROWS]
        for i, srow in enumerate(first_block, start=1):
            text = " | ".join(c for c in srow.cells if str(c).strip())[:90]
            r = QRadioButton(copy.get("preview.row", n=i, cells=text))
            r.setChecked(i == facts.header_row and not facts.header_is_virtual)
            self.group.addButton(r, i)
            pl.addWidget(r)
            self.radios.append(r)
            self.window_.run_hold.register(r)
        self.window_.run_hold.register(none)
        self.group.idClicked.connect(self.pick)
        self.content.addWidget(picker)
        if facts.continuation_blocks:
            self.content.addWidget(label(copy.get("preview.continues", n=facts.continuation_blocks), role="note", wrap=True))
        g = grid_with_pager(t.headers, t.rows)
        g.setMinimumHeight(420)
        self.grid = g
        self.content.addWidget(g)
        self.scroll.fit()

    def pick(self, n):
        if self.window_.run_hold.active:
            return
        facts = self.window_.bridge.survey().table(self.table_key)
        self.window_.bridge.dispatch(SetupChange("tables", (facts.file_name, facts.idx, "header_row"), n))
