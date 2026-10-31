"""The Process body."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QWidget

from wholecount import copy
from wholecount.session.commands import SetupChange
from wholecount.session.frame import backend_kind, stale_reason
from wholecount.ui.frame import a11y
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card, source_label
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.confidence import ConfidenceBlock
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.steplist import Bar, StepList
from wholecount.ui.widgets.style import button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tag import tag


def process_holds(session):
    """The holds on Process everything, first one first (M12 section 1.2). The run hold is added by RunHold."""
    from wholecount.session.survey import survey

    if session is None or not session.setup.paths():
        return [HoldReason("src.hold.no_table")]
    sv = survey(session)
    if not any(t.included for t in sv.tables):
        return [HoldReason("src.hold.no_table")]
    for b in sv.blocks:
        if b.kind == "ssn_shaped_id":
            return [HoldReason("map.ssn")]
        return [HoldReason("run.hold.blocker", {"field": b.field, "table": sv.table(b.table_key).file_name})]
    n = len(sv.program_map.unconfirmed) if sv.program_map else 0
    if n:
        return [HoldReason("run.hold.programs", {"n": n})]
    return []


def pre_run_lines(session, export_settings):
    """The four lines of What this run will do. Copy IDs and parameters only."""
    from wholecount.session.survey import survey

    sv = survey(session)
    tables = sum(1 for t in sv.tables if t.included)
    files = sum(1 for f in sv.files if f.status == "ok")
    steps = sum(1 for st in sv.steps.values() for s in st if not s.removed)
    kind = backend_kind(session.backend)
    maps = "run.pre.maps.default"
    if export_settings.exact_coordinates and export_settings.map_points:
        maps = "run.pre.maps.both"
    elif export_settings.exact_coordinates:
        maps = "run.pre.maps.coords"
    elif export_settings.map_points:
        maps = "run.pre.maps.points"
    lines = (("run.pre.reads", {"n": tables, "m": files}), ("run.pre.checks", {"k": steps}),
             (f"run.pre.backend.{kind}", {}), (maps, {}))
    from wholecount.session.crosswalk import state

    if state(session) == "orphaned":       # M13 XW-3: said before the run, so nobody expects earlier batches' IDs
        lines += (("run.pre.crosswalk_orphaned", {}),)
    return lines


class ProcessBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        self.process = HeldAction("run.process", "primary")
        self.process.setObjectName("processAll")
        self.process.clicked.connect(lambda: window.start_process())
        window.run_hold.register(self.process)
        self.cont = button(copy.get("run.continue"), "secondary", name="continueReview")
        self.cont.clicked.connect(lambda: window.go_to("review"))
        self.head = StageHead("run", [self.cont, self.process], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.panel_box = vbox(spacing=8)
        lay.addLayout(self.panel_box)
        self.summary_box = vbox(spacing=8)
        lay.addLayout(self.summary_box)
        self.settings_box = vbox(spacing=8)
        lay.addLayout(self.settings_box)
        self.found_box = vbox(spacing=8)
        lay.addLayout(self.found_box)
        self.conf_box = vbox(spacing=8)
        lay.addLayout(self.conf_box)
        lay.addStretch(1)
        self.show_log = False
        self.show_tables = False
        self.panel = None
        self.panel_state = None           # running, cancelling, cancelled, failed
        self.failure = None
        self.update_view(v)

    @property
    def session(self):
        return self.window_.bridge.session

    # The run panel

    def job_started(self, model):
        if model.action_id != "process":
            return
        self.panel_state = "running"
        self._panel(model)

    def job_progress(self, model):
        if self.panel_state in ("running", "cancelling") and model.action_id == "process":
            self._panel(model)

    def job_ended(self, how, code=None, step=None):
        if how == "cancelled":
            self.panel_state = "cancelled"
        elif how == "failed":
            self.panel_state, self.failure = "failed", (code, step)
        else:
            self.panel_state = None
        self._panel(None)

    def _cancel(self):
        self.panel_state = "cancelling"
        self.window_.bridge.cancel_job()
        self.cancel_button.setText(copy.get("run.cancelling"))

    def _panel(self, model):
        clear(self.panel_box)
        st = self.panel_state
        if st in ("running", "cancelling") and model is not None:
            c = Callout("needs")
            c.setObjectName("runPanel")
            c.body.addWidget(label(copy.get("run.panel.kicker").upper(), role="kicker"))
            i = max(0, model.current)
            top = hbox(spacing=10)
            top.addWidget(label(copy.get("run.panel.step", i=i + 1, n=len(model.steps),
                                         step=copy.get(model.steps[i].name_id)), role="row-title", name="panelStep"), 1)
            secs = sum(s.seconds or 0 for s in model.states)
            top.addWidget(label(copy.get("run.panel.elapsed", secs=f"{secs:.1f}"), role="note", name="panelElapsed"))
            self.cancel_button = button(copy.get("run.cancelling" if st == "cancelling" else "ticker.cancel"), "secondary",
                                        name="panelCancel")
            self.cancel_button.clicked.connect(self._cancel)
            top.addWidget(self.cancel_button)
            c.body.addLayout(top)
            bar = Bar(4)
            bar.set_fraction(model.overall_fraction())
            c.body.addWidget(bar)
            sl = StepList(model.steps)
            sl.show_model(model)
            c.body.addWidget(sl)
            self.panel = c
            self.panel_box.addWidget(c)
        elif st == "cancelled":
            f = QFrame()
            f.setObjectName("grayRow")
            fl = vbox(f, (14, 10, 14, 10))
            fl.addWidget(label(copy.get("run.cancelled"), role="note", name="panelCancelled"))
            self.panel_box.addWidget(f)
        elif st == "failed":
            code, step = self.failure
            c = Callout("wrong")
            c.setObjectName("runFailed")
            name = copy.get(f"progress.step.{step.value}") if step is not None else copy.get("action.process")
            c.body.addWidget(label(copy.get("run.failed", step=name), role="row-title", tone="amber", wrap=True))
            c.body.addWidget(label(copy.get("ticker.error_code", code=code), role="note", name="errorCode"))
            row = hbox(spacing=8)
            again = button(copy.get("run.try_again"), "primary", name="tryAgain")
            again.clicked.connect(lambda: self.window_.start_process())
            self.window_.run_hold.register(again)
            cp = button(copy.get("run.copy_code"), "quiet", "nav", name="copyCode")
            cp.clicked.connect(lambda: self._copy(code))
            row.addWidget(again)
            row.addWidget(cp)
            row.addStretch(1)
            c.body.addLayout(row)
            self.panel_box.addWidget(c)
        else:
            self._folded()

    def _copy(self, code):
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(code)

    def _folded(self):
        s = self.session
        if s is None or s.results is None:
            return
        f = QFrame()
        f.setObjectName("amberRow" if s.stale else "card")
        fl = vbox(f, (14, 6, 14, 6), 6)
        row = hbox(spacing=8)
        if s.stale:
            what = copy.get(f"run.stale.{stale_reason(s)}")
            row.addWidget(label(copy.get("run.out_of_date", what=what), role="note", tone="amber", name="foldedLine"), 1)
        else:
            secs = self.window_.bridge.ui.get("run_seconds")
            text = copy.get("run.done.line", secs=f"{secs:.1f}", n=7) if secs is not None else copy.get("run.up_to_date")
            row.addWidget(label(text, role="note", name="foldedLine"), 1)
        log = button(copy.get("ticker.show_log"), "quiet", "nav", name="runShowLog")
        log.clicked.connect(self._toggle_log)
        row.addWidget(log)
        fl.addLayout(row)
        model = self.window_.model
        if self.show_log and model is not None and model.action_id == "process":
            grid = QGridLayout()
            for i, k in enumerate(("step", "took", "found")):
                grid.addWidget(label(copy.get(f"run.log.{k}"), role="column-head"), 0, i)
            from wholecount.session.progress import render

            for r, (sd, st) in enumerate(zip(model.steps, model.states), start=1):
                grid.addWidget(label(copy.get(sd.name_id), role="note"), r, 0)
                grid.addWidget(label(f"{(st.seconds or 0):.1f} s", role="note"), r, 1)
                grid.addWidget(label(render(st.found) if st.found is not None else "", role="caption", wrap=True), r, 2)
            grid.setColumnStretch(2, 1)
            fl.addLayout(grid)
        self.panel_box.addWidget(f)

    def _toggle_log(self):
        self.show_log = not self.show_log
        self._panel(None)

    # Before a run

    def _summary(self):
        clear(self.summary_box)
        s = self.session
        if s is None or not s.setup.paths() or (s.results is not None and not s.stale):
            return
        c = Callout("ink")
        c.setObjectName("preRun")
        c.body.addWidget(label(copy.get("run.pre.kicker").upper(), role="kicker"))
        for key, params in pre_run_lines(s, self.window_.bridge.export_settings()):
            amber = key == "run.pre.backend.none"
            row = hbox(spacing=8)
            row.addWidget(label(copy.get(key, **params), role="note", tone="amber" if amber else "ink", wrap=True,
                                name=key.replace(".", "_")), 1)
            if key.startswith("run.pre.maps"):
                ch = button(copy.get("run.pre.change"), "quiet", "nav", name="changeMaps")
                ch.clicked.connect(lambda: self.window_.go_to("export"))
                row.addWidget(ch)
            c.body.addLayout(row)
        self.summary_box.addWidget(c)

    def _settings(self):
        clear(self.settings_box)
        s = self.session
        if s is None:
            return
        c = Card()
        c.setObjectName("runSettings")
        c.body.addWidget(label(copy.get("run.settings.kicker").upper(), role="kicker"))
        row = hbox(spacing=8)
        row.addWidget(label(copy.get("run.settings.geocoder"), role="row-title"))
        kind = backend_kind(s.backend)
        row.addWidget(label(copy.get(f"run.settings.backend.{kind}"), role="note"))
        ready = kind != "none"
        row.addWidget(tag(copy.get("run.settings.ready" if ready else "run.settings.not_installed"),
                          "confirmed" if ready else "wrong"))
        row.addStretch(1)
        c.body.addLayout(row)
        if kind in ("reference", "practice"):
            c.body.addWidget(label(copy.get("run.settings.reference_rows", n=getattr(s.backend, "rows", 0)), role="caption"))
        pre = self.window_.bridge.preflight
        if pre is not None and pre.reference_kind == "several_reference_files":
            c.body.addWidget(label(copy.get("run.settings.two_files"), role="caption", tone="amber"))
        c.body.addWidget(label(copy.get("run.settings.local"), role="caption", wrap=True))
        c.body.addWidget(label(copy.get("run.settings.extra"), role="row-title"))
        chosen = set(s.setup.get("run_settings", "extra_fields", frozenset()) or ())
        row = hbox(spacing=8)
        on_geo = s.backend.name == "geosupport"
        from wholecount.session.frame import extra_geo_fields

        for fld in extra_geo_fields():
            b = button(copy.get(f"run.settings.field.{fld}"), "chip", name=f"extra_{fld}")
            set_prop(b, "selected", fld in chosen)
            b.setEnabled(on_geo)
            b.clicked.connect(lambda _=False, f=fld: self._toggle_extra(f))
            self.window_.run_hold.register(b)
            row.addWidget(b)
        row.addWidget(label(copy.get("run.settings.selected", n=len(chosen)), role="caption"))
        row.addStretch(1)
        c.body.addLayout(row)
        if not on_geo:
            c.body.addWidget(label(copy.get("run.settings.extra_off"), role="caption", wrap=True))
        self.settings_box.addWidget(c)

    def _toggle_extra(self, fld):
        s = self.session
        chosen = set(s.setup.get("run_settings", "extra_fields", frozenset()) or ())
        chosen ^= {fld}
        self.window_.bridge.dispatch(SetupChange("run_settings", "extra_fields", frozenset(chosen)))

    # After a run

    def _found(self, v):
        clear(self.found_box)
        s = self.session
        if s is None or s.results is None or s.stale or v.counts is None:
            return
        c = Callout("ink")
        c.setObjectName("runFound")
        c.body.addWidget(label(copy.get("run.found.kicker").upper(), role="kicker"))
        (k1, rows), (k2, loc) = v.counts.lines
        c.body.addWidget(label(copy.get("run.found.balance", counted=rows["counted"], not_counted_yet=rows["not_counted_yet"],
                                        aside=rows["set_aside"], received=rows["received"]), role="count-row",
                               name="foundBalance"))
        c.body.addWidget(label(copy.get("run.found.balance_note"), role="note"))
        c.body.addWidget(label(copy.get("run.found.loc_sum", high=loc["high"], low=loc["low"], not_mapped=loc["not_mapped"],
                                        counted=loc["counted"]), role="count-row", name="foundLoc"))
        c.body.addWidget(label(copy.get("run.found.loc"), role="note"))
        boxes = hbox(spacing=10)
        for key, n, tone, status in (("counted", rows["counted"], "ink", "approved"),
                                     ("not_counted_yet", rows["not_counted_yet"], "blue", "open"),
                                     ("set_aside", rows["set_aside"], "muted", "set_aside")):
            b = Card()
            b.body.addWidget(label(copy.get(f"run.found.box.{key}"), role="caption"))
            b.body.addWidget(label(f"{n:,}", role="count", tone=tone if tone != "ink" else None, name=f"box_{key}"))
            b.body.addWidget(label(copy.get(f"run.found.box.{key}_means"), role="caption", wrap=True))
            go = button(copy.get("run.found.see"), "quiet", "nav", name=f"see_{key}")
            go.clicked.connect(lambda _=False, st=status: self.window_.open_queue(st))
            b.body.addWidget(go, 0, Qt.AlignLeft)
            boxes.addWidget(b, 1)
        c.body.addLayout(boxes)
        t = button(copy.get("run.found.per_table"), "quiet", "nav", name="perTable")
        t.clicked.connect(self._toggle_tables)
        c.body.addWidget(t, 0, Qt.AlignLeft)
        bal = s.results.balance
        ok = all(x.received == x.counted + x.not_counted_yet + x.set_aside and x.counted == x.mapped + x.counted_not_mapped
                 for x in bal.tables)
        if self.show_tables:
            names = {w.table.key: (w.table.letter, w.file_name) for w in s.results.works}
            for x in bal.tables:
                good = x.received == x.counted + x.not_counted_yet + x.set_aside and x.counted == x.mapped + x.counted_not_mapped
                f = QFrame()
                f.setObjectName("card" if good else "amberRow")
                fl = hbox(f, (10, 4, 10, 4), 8)
                letter, fname = names.get(x.table_key, ("?", x.table_key))
                fl.addWidget(source_label(letter, fname, role="note"), 1)
                fl.addWidget(label(copy.get("run.found.table_line", c=x.counted, n=x.not_counted_yet, a=x.set_aside,
                                            m=x.mapped, u=x.counted_not_mapped, r=x.received), role="caption"))
                c.body.addWidget(f)
        if not ok:
            c.body.addWidget(label(copy.get("run.found.fault"), role="note", tone="amber", wrap=True, name="foundFault"))
        c.body.addWidget(label(copy.get("run.found.outside", a=bal.excluded_rows, b=bal.non_table_rows,
                                        c=bal.above_header_rows), role="note", wrap=True, name="foundOutside"))
        self.found_box.addWidget(c)

    def _toggle_tables(self):
        self.show_tables = not self.show_tables
        self._found(self.window_.view)

    def _confidence(self, v):
        clear(self.conf_box)
        if v.confidence is None or v.confidence.level is None or v.running:
            return
        c = Callout("ink" if v.confidence.level == "high" else "wrong")
        c.setObjectName("confidenceCallout")
        block = ConfidenceBlock(v, full=True, on_tick=self.window_.acknowledge_low)
        self.window_.run_hold.register(block.tick.check) if block.tick is not None else None
        c.body.addWidget(block)
        from wholecount.ui.widgets.confidence import measure_rows

        for name, value, need, miss in measure_rows(v.confidence):
            c.body.addWidget(label(f"{name}: {value}. {need}", role="caption", tone="amber" if miss else None, wrap=True))
        codes = {code for code, _ in v.confidence.parts}
        row = hbox(spacing=8)
        if "counted_short" in codes:
            b = button(copy.get("run.go_review"), "primary", name="goReview")
            b.clicked.connect(lambda: self.window_.go_to("review"))
            row.addWidget(b)
        if "pairs_open" in codes:
            b = button(copy.get("run.go_results"), "primary", name="goResults")
            b.clicked.connect(lambda: self.window_.go_to("summary"))
            row.addWidget(b)
        row.addStretch(1)
        c.body.addLayout(row)
        self.conf_box.addWidget(c)

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        s = self.session
        ran = s is not None and s.results is not None
        self.process.set_label("run.process_again" if ran else "run.process")
        self.process.set_holds(process_holds(s))
        self.cont.setVisible(ran)
        if self.panel_state not in ("running", "cancelling"):
            self._panel(None)
        self._summary()
        self._settings()
        self._found(v)
        self._confidence(v)


def build(stage_id, window):
    return ProcessBody(window)
