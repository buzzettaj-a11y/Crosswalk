"""The Add your files body."""
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QFrame, QLineEdit, QWidget

from wholecount import copy
from wholecount.session.commands import SetKeepSensitive, SetupChange
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card, source_label
from wholecount.ui.stages.sources import drop
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.saved_progress_card import SavedProgressCard
from wholecount.ui.widgets.setups import SetupsPanel
from wholecount.ui.widgets.source_mark import SourceMark
from wholecount.ui.widgets.style import narrow_combo, button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tag import tag

SAMPLE = pathlib.Path(__file__).resolve().parents[3] / "sample_data"
EXAMPLES = ("example_clinic.csv", "example_housing.xlsx", "example_partner.tsv", "example_portal.json", "example_state.xml")
SHOWN_TABLES = 4


def fast_path_holds(sv, schema_keys=None):
    """The fast path's holds, first one that applies (M11 section 1.3)."""
    if sv is None or not any(t.included for t in sv.tables):
        return [HoldReason("src.hold.no_table")]
    if not all(f.balanced for f in sv.files if f.status == "ok"):
        return [HoldReason("src.hold.unbalanced")]
    holds = []
    blocks = list(sv.blocks)
    if blocks:
        b = blocks[0]
        if b.kind == "ssn_shaped_id":
            holds.append(HoldReason("map.ssn"))
        else:
            name = sv.table(b.table_key).file_name
            more = len(blocks) - 1
            holds.append(HoldReason("src.hold.blocker_more" if more else "src.hold.blocker",
                                    {"table": name, "field": b.field, **({"n": more} if more else {})}))
    return holds


class DropZone(QFrame):
    def __init__(self, stage, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        lay = vbox(self, (18, 16, 18, 16), 8)
        self.title = label(copy.get("src.drop.title"), role="row-title", name="dropTitle")
        self.note = label(copy.get("src.drop.note"), role="note", wrap=True)
        lay.addWidget(self.title)
        lay.addWidget(self.note)
        row = hbox(spacing=8)
        self.browse = HeldAction("src.drop.browse", "secondary")
        self.example = HeldAction("src.drop.example", "quiet")
        self.browse.setObjectName("browse")
        self.example.setObjectName("example")
        row.addWidget(self.browse)
        row.addWidget(self.example)
        row.addStretch(1)
        lay.addLayout(row)
        self.message = label("", role="note", name="dropMessage", wrap=True)
        lay.addWidget(self.message)
        self.message.hide()
        self.state = None

    # The zone is part of the stage's drop target; it hands drag events to the stage body.
    def dragEnterEvent(self, ev):
        self.stage.dragEnterEvent(ev)

    def dragMoveEvent(self, ev):
        self.stage.dragMoveEvent(ev)

    def dragLeaveEvent(self, ev):
        self.stage.dragLeaveEvent(ev)

    def dropEvent(self, ev):
        self.stage.dropEvent(ev)

    def set_state(self, state, text=None):
        self.state = state
        set_prop(self, "drop", state or "")
        self.message.setVisible(bool(text))
        self.message.setText(text or "")
        if state is None:
            self.title.setText(copy.get("src.drop.title"))


class SourcesBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setAcceptDrops(True)
        window.drop_guard.add(self)
        lay = vbox(self, spacing=16)
        v = window.view
        self.head = StageHead("sources", saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.resume_box = vbox(spacing=8)
        lay.addLayout(self.resume_box)
        self.fast = self._fast_card()
        lay.addWidget(self.fast)
        self.zone = DropZone(self)
        self.zone.browse.clicked.connect(self.browse)
        self.zone.example.clicked.connect(self.use_example)
        for w in (self.zone.browse, self.zone.example):
            window.run_hold.register(w)
        lay.addWidget(self.zone)
        self.notices = vbox(spacing=8)
        lay.addLayout(self.notices)
        self.systems = vbox(spacing=8)
        lay.addLayout(self.systems)
        self.list = vbox(spacing=8)
        lay.addLayout(self.list)
        self.accounted = vbox(spacing=8)
        lay.addLayout(self.accounted)
        self.setups = SetupsPanel(window)
        lay.addWidget(self.setups)
        lay.addStretch(1)
        self.show_all = False
        self.warning = None
        self.update_view(v)

    # Fast path

    def _fast_card(self):
        c = Callout("needs")
        c.setObjectName("fastPath")
        c.body.addWidget(label(copy.get("src.fast.title"), role="h3"))
        c.body.addWidget(label(copy.get("src.fast.body"), role="note", tone="ink-2", wrap=True))
        self.process_all = HeldAction("src.fast.button", "primary")
        self.process_all.setObjectName("processEverything")
        self.process_all.clicked.connect(self.fast_path)
        self.window_.run_hold.register(self.process_all)
        c.body.addWidget(self.process_all, 0, Qt.AlignLeft)
        self.fast_extra = vbox(spacing=6)
        c.body.addLayout(self.fast_extra)
        row = hbox(spacing=8)
        row.addWidget(label(copy.get("src.fast.or"), role="note"))
        go = button(copy.get("src.fast.continue"), "quiet", "nav", name="continueSchema")
        go.clicked.connect(lambda: self.window_.go_to("schema"))
        row.addWidget(go)
        row.addStretch(1)
        c.body.addLayout(row)
        return c

    def fast_path(self):
        w = self.window_
        sv = w.bridge.survey()
        clear(self.fast_extra)
        if sv is None:
            return
        problems = sum(1 for wk in sv.works.values() for chk in wk.mapping.checks.values() if chk.status == "problem")
        if problems and not self.warning:
            self.warning = Callout("wrong")
            self.warning.body.addWidget(label(copy.get("src.fast.wrong", n=problems), role="note", tone="amber", wrap=True))
            row = hbox(spacing=8)
            fix = button(copy.get("src.fast.fix_first"), "primary", name="fixFirst")
            fix.clicked.connect(lambda: w.go_to("map"))
            anyway = button(copy.get("src.fast.run_anyway"), "secondary", name="runAnyway")
            anyway.clicked.connect(self._run_anyway)
            row.addWidget(fix)
            row.addWidget(anyway)
            row.addStretch(1)
            self.warning.body.addLayout(row)
            self.fast_extra.addWidget(self.warning)
            return
        self._go(sv)

    def _run_anyway(self):
        self._go(self.window_.bridge.survey())

    def _go(self, sv):
        w = self.window_
        self.warning = None
        if sv.program_map is not None and sv.program_map.unconfirmed:
            w.program_notice = len(sv.program_map.unconfirmed)
            w.go_to("programs")
            return
        w.start_process(then="review")

    # Files

    def browse(self):
        paths, _ = QFileDialog.getOpenFileNames(self, copy.get("src.drop.browse"), "", copy.get("src.drop.filter"))
        if paths:
            self.window_.add_files([pathlib.Path(p) for p in paths])

    def use_example(self):
        self.window_.use_example_data([SAMPLE / n for n in EXAMPLES])

    def dragEnterEvent(self, ev):
        if self.window_.run_hold.active:
            self.zone.set_state("bad", copy.get("hold.run"))
            ev.ignore()
            return
        paths, problem = drop.dropped_paths(ev.mimeData())
        if problem:
            self.zone.set_state("bad", copy.get(f"src.drop.{problem}"))
            ev.ignore()
            return
        self.zone.set_state("ok")
        self.zone.title.setText(copy.get("src.drop.over", n=len(paths)))
        ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        if self.zone.state == "ok":
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragLeaveEvent(self, ev):
        self.zone.set_state(None)

    def dropEvent(self, ev):
        paths, problem = drop.dropped_paths(ev.mimeData())
        if problem or self.window_.run_hold.active:
            ev.ignore()
            return
        self.zone.set_state(None)
        ev.acceptProposedAction()
        self.window_.add_files(paths)

    # Drawing

    def update_view(self, v):
        sv = self.window_.bridge.survey()
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        self.process_all.set_holds(fast_path_holds(sv))
        self._resume()
        self._notices(sv)
        self._systems(sv)
        self._tables(sv)
        self._accounted(sv)

    def _resume(self):
        clear(self.resume_box)
        for entry in self.window_.bridge.saved_progress_entries():
            card = SavedProgressCard(entry)
            row = hbox(spacing=8)
            res = button(copy.get("src.resume"), "secondary", name="resume")
            res.clicked.connect(lambda _=False, e=entry: self.window_.resume(e))
            dele = button(copy.get("src.resume_delete"), "quiet", "lesser", name="deleteSaved")
            dele.clicked.connect(lambda _=False, e=entry: self.window_.delete_saved(e))
            self.window_.run_hold.register(res)
            row.addWidget(res)
            row.addWidget(dele)
            row.addStretch(1)
            card.layout().addLayout(row)
            self.resume_box.addWidget(card)

    def _notices(self, sv):
        clear(self.notices)
        ui = self.window_.bridge.ui
        if ui.get("example_loaded"):
            c = Callout("needs")
            c.setObjectName("exampleNotice")
            c.body.addWidget(label(copy.get("src.example_loaded"), role="note", tone="blue", wrap=True))
            self.notices.addWidget(c)
        plan = ui.get("resume_plan")
        for name in (plan.changed if plan else ()):
            c = Callout("wrong")
            c.setObjectName("resumeChanged")
            c.body.addWidget(label(copy.get("src.resume_changed", name=name), role="note", tone="amber", wrap=True))
            self.notices.addWidget(c)
        for msg in ui.get("add_messages", ()):
            self.notices.addWidget(label(copy.get(msg[0], **msg[1]), role="note", tone="amber", wrap=True))
        if sv is None:
            return
        for f in sv.files:
            if f.status == "unreadable":
                c = Callout("wrong")
                c.setObjectName("unreadable")
                c.body.addWidget(label(copy.get("src.unreadable", name=f.name,
                                                 reason=copy.get(f"read.unreadable.{f.reason_id}")), role="note",
                                       tone="amber", wrap=True))
                self.notices.addWidget(c)
            elif f.status == "duplicate_file":
                self.notices.addWidget(label(copy.get("src.already_added", name=f.name), role="note", tone="amber"))
            if f.encoding == "windows-1252":
                c = Callout("wrong")
                c.setObjectName("encoding")
                c.body.addWidget(label(copy.get("read.encoding_note"), role="note", wrap=True))
                for s in f.encoding_samples[:5]:
                    c.body.addWidget(label(s, role="caption"))
                self.notices.addWidget(c)
            if f.sensitive:
                c = Callout("wrong")
                c.setObjectName("sensitive")
                c.body.addWidget(label(copy.get("src.sensitive.title", name=f.name), role="row-title"))
                for col, why in f.sensitive:
                    box = QCheckBox(copy.get("src.sensitive.drop", column=col, reason=copy.get(f"src.sensitive.{why}")))
                    box.setChecked(col not in self.window_.bridge.session.keep_sensitive)
                    box.toggled.connect(lambda on, col=col: self.sensitive(col, on))
                    self.window_.run_hold.register(box)
                    c.body.addWidget(box)
                self.notices.addWidget(c)
            if drop.on_network_drive(f.name):
                self.notices.addWidget(label(copy.get("src.network_drive", name=f.name), role="note", tone="amber"))
        for name in ui.get("corrections_files", ()):
            self.notices.addWidget(label(copy.get("src.corrections_file", name=name), role="note", tone="blue", wrap=True))

    def sensitive(self, column, drop_it):
        w = self.window_
        if not drop_it:
            if not w.confirm(copy.get("src.sensitive.keep_title"), (copy.get("src.sensitive.keep_q", column=column),),
                             copy.get("src.sensitive.keep"), copy.get("close.keep")):
                self.update_view(w.view)
                return
        w.bridge.dispatch(SetKeepSensitive(column, not drop_it))

    def _systems(self, sv):
        clear(self.systems)
        files = [f for f in (sv.files if sv else ()) if f.status == "ok"]
        if len(files) < 2:
            return
        c = Card()
        c.setObjectName("systemsCard")
        c.body.addWidget(label(copy.get("src.systems.title"), role="row-title"))
        c.body.addWidget(label(copy.get("src.systems.body"), role="note", wrap=True))
        setup = self.window_.bridge.session.setup
        for f in files:
            row = hbox(spacing=8)
            row.addWidget(SourceMark(f.letter))
            row.addWidget(label(f.name, role="note"), 1)
            sel = QComboBox()
            narrow_combo(sel)
            sel.setObjectName(f"system_{f.letter}")
            sel.addItem(copy.get("src.systems.own"), "")
            for o in files:
                if o.name != f.name:
                    sel.addItem(copy.get("src.systems.with", name=sv.systems.get(o.letter, o.name)), o.name)
            cur = setup.get("systems", ("member", f.name))
            sel.setCurrentIndex(max(0, sel.findData(cur or "")))
            sel.currentIndexChanged.connect(lambda _, s=sel, f=f: self.window_.bridge.dispatch(
                SetupChange("systems", ("member", f.name), s.currentData() or None)))
            name = QLineEdit(sv.systems.get(f.letter, ""))
            name.setObjectName(f"system_name_{f.letter}")
            name.editingFinished.connect(lambda n=name, f=f: n.text().strip() and n.text().strip() != sv.systems.get(f.letter)
                                         and self.window_.bridge.dispatch(SetupChange("systems", ("name", f.name),
                                                                                       n.text().strip())))
            for x in (sel, name):
                self.window_.run_hold.register(x)
            row.addWidget(sel)
            row.addWidget(name)
            c.body.addLayout(row)
        self.systems.addWidget(c)

    def _tables(self, sv):
        clear(self.list)
        if sv is None:
            return
        by_file = {}
        for t in sv.tables:
            by_file.setdefault(t.file_name, []).append(t)
        shown = 0
        hidden = 0
        for fname, ts in by_file.items():
            ts = sorted(ts, key=lambda t: (not (t.header_warning or t.kind != "records"), t.idx))
            for i, t in enumerate(ts):
                if shown >= SHOWN_TABLES and not self.show_all:
                    hidden += 1
                    continue
                self.list.addWidget(self._table_row(t, first=i == 0))
                shown += 1
        if hidden:
            row = hbox(spacing=8)
            row.addWidget(label(copy.get("src.more_tables", n=hidden), role="note"))
            more = button(copy.get("src.show_them"), "quiet", "nav", name="showTables")
            more.clicked.connect(self._show_all)
            row.addWidget(more)
            row.addStretch(1)
            self.list.addLayout(row)

    def _show_all(self):
        self.show_all = True
        self._tables(self.window_.bridge.survey())

    def _table_row(self, t, first):
        c = Card()
        c.setObjectName("tableRow")
        row = hbox(spacing=10)
        box = QCheckBox()
        box.setObjectName(f"include_{t.letter}_{t.idx}")
        box.setChecked(t.included)
        box.setAccessibleName(copy.get("src.include", name=t.file_name))
        box.toggled.connect(lambda on, t=t: self.window_.bridge.dispatch(
            SetupChange("tables", (t.file_name, t.idx, "included"), on)))
        self.window_.run_hold.register(box)
        row.addWidget(box, 0, Qt.AlignTop)
        mid = vbox(spacing=4)
        top = hbox(spacing=8)
        top.addWidget(source_label(t.letter, t.file_name))
        top.addWidget(label(t.location, role="micro"))
        top.addWidget(tag(copy.get("src.tag.records" if t.kind == "records" else "src.tag.not_records"), "neutral"))
        if t.dob_present:
            top.addWidget(tag(copy.get("src.tag.dob"), "neutral"))
        if t.header_warning:
            top.addWidget(tag(copy.get("src.tag.header"), "wrong"))
        if t.continuation_blocks:
            top.addWidget(tag(copy.get("src.tag.continues", n=t.continuation_blocks), "neutral"))
        top.addStretch(1)
        mid.addLayout(top)
        line = copy.get("src.table_line", rows=t.rows, cols=t.columns, pct=t.filled_pct)
        line += " " + copy.get("src.recognized" if t.kind == "records" else "src.not_records")
        mid.addWidget(label(line, role="caption", wrap=True))
        row.addLayout(mid, 1)
        show = button(copy.get("src.show_data"), "quiet", "nav", name=f"show_{t.letter}_{t.idx}")
        show.clicked.connect(lambda _=False, k=t.key: self.window_.show_data(k))
        row.addWidget(show, 0, Qt.AlignTop)
        if first:
            rm = HeldAction("src.remove_file", "quiet")
            rm.setObjectName(f"remove_{t.letter}")
            rm.clicked.connect(lambda t=t: self.remove(t))
            self.window_.run_hold.register(rm)
            row.addWidget(rm, 0, Qt.AlignTop)
        c.body.addLayout(row)
        return c

    def remove(self, t):
        w = self.window_
        if not w.confirm(copy.get("src.remove_title"), (copy.get("src.remove_q", name=t.file_name),),
                         copy.get("src.remove_file"), copy.get("close.keep")):
            return
        path = next((str(p) for p in w.bridge.session.setup.paths() if pathlib.Path(p).name == t.file_name), None)
        if path:
            w.bridge.dispatch(SetupChange("sources", path, False))

    def _accounted(self, sv):
        clear(self.accounted)
        files = [f for f in (sv.files if sv else ()) if f.status == "ok"]
        if not files:
            return
        ok = all(f.balanced for f in files)
        c = Callout("ink" if ok else "wrong")
        c.setObjectName("accounted")
        c.body.addWidget(label(copy.get("src.accounted.title"), role="row-title"))
        for f in files:
            c.body.addWidget(label(copy.get("src.accounted.file", name=f.name, a=f.in_tables, b=f.in_excluded,
                                            c=f.not_tables, d=f.above_header, h=f.header_rows, total=f.total),
                                   role="note", wrap=True, tone=None if f.balanced else "amber"))
        totals = [sum(getattr(f, k) for f in files) for k in ("in_tables", "in_excluded", "not_tables", "above_header",
                                                              "header_rows", "total")]
        c.body.addWidget(label(copy.get("src.accounted.batch", a=totals[0], b=totals[1], c=totals[2], d=totals[3],
                                        h=totals[4], total=totals[5]), role="note", wrap=True, name="accountedBatch"))
        if not ok:
            c.body.addWidget(label(copy.get("src.accounted.wrong"), role="note", tone="amber", wrap=True))
        self.accounted.addWidget(c)


def build(stage_id, window):
    return SourcesBody(window)
