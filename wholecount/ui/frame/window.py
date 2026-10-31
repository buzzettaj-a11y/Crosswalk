"""MainWindow (SPEC 11.1 to 11.4): top bar, stage strip, run ticker, ledger band, then the ledger column and the stage area.

Under 1360 wide (compact) the ledger column hides, the band shows, Close moves into the top bar, and the one LedgerPanel
moves into the Details drawer when that opens. Crossing the breakpoint keeps scroll positions, the open drawer and every
held state.
"""
import datetime as dt
import pathlib

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMainWindow, QWidget

from wholecount import brand, copy
from wholecount.ui.frame import a11y
from wholecount.ui.frame.band import LedgerBand
from wholecount.ui.frame.close import ask, close_lines, start_over_lines
from wholecount.ui.frame.drawers import DetailsDrawer, SettingsDrawer, SystemCheckDrawer, YourDataDrawer
from wholecount.ui.frame.ledger import LedgerPanel, stage_section_for
from wholecount.ui.frame.stages import BY_ID
from wholecount.ui.frame.strip import StageStrip
from wholecount.ui.frame.ticker import Dropdown, LogView, RunTicker, steplist_for
from wholecount.ui.frame.topbar import TopBar
from wholecount.ui.jobs.model import ProgressModel
from wholecount.ui.stages import StageRegistry
from wholecount.ui.widgets.held import RunHold
from wholecount.ui.widgets.style import WrapScroll, hbox, vbox

BREAKPOINT = 1360
MIN_W, MIN_H = 1280, 720
OPEN_W, OPEN_H = 1440, 980
SAVED_REFRESH_MS = 30_000


class ReviewerDialog:
    """One line edit. Fires SetReviewer once with the typed name, and shows M08's refusal for a bad one."""

    def __init__(self, window):
        self.window = window

    def run(self, name=None):
        from wholecount.session.commands import SetReviewer
        from wholecount.session.reviewer import BadReviewerName, settings

        if name is None:
            name, ok = QInputDialog.getText(self.window, copy.get("reviewer.title"), copy.get("reviewer.prompt"),
                                            QLineEdit.Normal, self.window.view.reviewer or "")
            if not ok:
                return None
        try:
            cmd = SetReviewer(name)
        except BadReviewerName as exc:
            params = {"max": settings()["reviewer_name_max"]} if exc.code == "too_long" else {}
            return copy.get(f"reviewer.refused.{exc.code}", **params)
        self.window.bridge.dispatch(cmd)
        return None


class MainWindow(QMainWindow):
    def __init__(self, bridge, registry=None, clock=None, confirm=None, start_over=None):
        super().__init__()
        self.bridge = bridge
        self.registry = registry or StageRegistry()
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.confirm = confirm or (lambda title, lines, yes, no: ask(self, title, lines, yes, no))
        self._start_over = start_over or bridge.start_over
        self.on_process = lambda: None
        self.setWindowTitle(brand.PRODUCT_NAME)
        self.setMinimumSize(MIN_W, MIN_H)
        self.run_hold = RunHold(self)
        from wholecount.ui.stages.sources.drop import guard
        from wholecount.ui.widgets.grid import GridStates

        self.drop_guard = guard()
        self.grid_states = GridStates()
        self.program_notice = None
        self.queue_request = None
        self.active_dialog = None
        self.toast = None
        self.ask_text = self._ask_text
        self._after_job = None
        self.model = None
        self.current = "sources"
        self.compact = None
        self.closing_confirmed = False
        self.close_requests = 0
        self.view = bridge.view()

        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        col = vbox(central)
        self.topbar = TopBar(self.request_close)
        self.strip = StageStrip(self.bridge_undo)
        self.strip.go.connect(self.go_to)
        self.run_hold.register(self.strip.undo)
        self.ticker = RunTicker()
        self.band = LedgerBand()
        for w in (self.topbar, self.strip, self.ticker, self.band):
            col.addWidget(w)
        body = QWidget()
        row = hbox(body)
        self.ledger_column = QWidget()
        self.ledger_column.setFixedWidth(280)
        self.column_lay = vbox(self.ledger_column)
        self.ledger = LedgerPanel()
        self.column_lay.addWidget(self.ledger)
        row.addWidget(self.ledger_column)
        self.stage_area = WrapScroll()
        self.stage_area.setObjectName("stageArea")
        row.addWidget(self.stage_area, 1)
        col.addWidget(body, 1)

        self.dropdown = Dropdown(central)
        self.details = DetailsDrawer(central)
        self.your_data = YourDataDrawer(central)
        self.check = SystemCheckDrawer(central)
        self.settings = SettingsDrawer(central)
        from wholecount.ui.widgets.preview import DataPreview

        self.preview = DataPreview(central, self)
        self.drawers = (self.details, self.your_data, self.check, self.settings, self.preview)
        self.details.closed.connect(self._details_closed)
        a11y.install(central)

        L = self.ledger
        L.open_check.connect(self.check.open_)
        L.open_your_data.connect(self.your_data.open_)
        L.open_settings.connect(self.settings.open_)
        L.change_reviewer.connect(self.change_reviewer)
        L.close_app.connect(self.request_close)
        L.start_over.connect(self.request_start_over)
        L.acknowledge.connect(self.acknowledge_low)
        self.run_hold.register(L.change)
        self.run_hold.register(self.settings.change)
        from wholecount.ui.settings.drawer import install

        self.m13 = install(self)
        self.band.details.connect(self.open_details)
        self.your_data.saved_toggled.connect(self.toggle_saved)
        # M15: the user guide opens from the Your data link and from F1.
        from PySide6.QtGui import QKeySequence, QShortcut

        self.your_data.open_guide.connect(self.open_guide)
        self.guide_shortcut = QShortcut(QKeySequence(Qt.Key_F1), self)
        self.guide_shortcut.activated.connect(self.open_guide)
        self.guide = None
        self.settings.saved_toggled.connect(self.toggle_saved)
        self.settings.change_reviewer.connect(self.change_reviewer)
        self.ticker.all_steps.connect(self.toggle_steps)
        self.ticker.show_log.connect(self.toggle_log)
        self.ticker.cancel.connect(self.bridge.cancel_job)

        r = bridge.runner
        r.step_begun.connect(self._step_begun)
        r.progressed.connect(self._progressed)
        r.step_ended.connect(self._step_ended)
        r.finished.connect(self._finished)
        r.cancelled.connect(self._cancelled)
        r.failed.connect(self._failed)
        bridge.changed.connect(self.refresh)

        self.saved_timer = QTimer(self)
        self.saved_timer.setInterval(SAVED_REFRESH_MS)
        self.saved_timer.timeout.connect(self._refresh_saved)
        self.saved_timer.start()

        self._open_size()
        self.apply_mode(self.width() < BREAKPOINT)
        self.go_to("sources")

    # Size and mode

    def _open_size(self):
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry().size() if screen else QSize(OPEN_W, OPEN_H)
        self.resize(min(OPEN_W, max(MIN_W, avail.width())), min(OPEN_H, max(MIN_H, avail.height())))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.apply_mode(self.width() < BREAKPOINT)
        for d in self.drawers:
            if d.isVisible():
                d.relayout()

    def apply_mode(self, compact):
        if compact == self.compact:
            return
        scroll = self.stage_area.verticalScrollBar().value()
        self.compact = compact
        self.topbar.set_compact(compact)
        self.strip.set_compact(compact)
        self.ledger.set_compact(compact)
        self.band.setVisible(compact)
        self.ledger_column.setVisible(not compact)
        if not self.details.isVisible():
            self._panel_to_column()
        self.stage_area.verticalScrollBar().setValue(scroll)

    def _panel_to_column(self):
        if self.ledger.parentWidget() is not self.ledger_column:
            self.column_lay.addWidget(self.ledger)
            self.ledger.show()

    def open_details(self):
        self.details.hold(self.ledger)
        self.details.open_()

    def _details_closed(self):
        self._panel_to_column()
        self.band.details_button.setFocus(Qt.OtherFocusReason) if self.compact else None

    # Stages

    def go_to(self, stage_id):
        self.previous_stage = getattr(self, "current", None)
        self.current = stage_id
        if getattr(self.bridge, "session", None) is not None:
            self.bridge.session.stage = stage_id
        old = self.stage_area.takeWidget()
        if old is not None:
            old.deleteLater()
        holder = QWidget()
        holder.setObjectName("stageBody")
        lay = vbox(holder, (24, 20, 24, 20))
        self.stage_widget = self.registry.build(stage_id, self)
        lay.addWidget(self.stage_widget)
        self.stage_area.setWidget(holder)
        self.stage_area.verticalScrollBar().setValue(0)
        self.ledger.set_stage_section(stage_section_for(stage_id, self.view))
        self.refresh()

    # Drawing

    def refresh(self):
        self.view = v = self.bridge.view()
        now = self.clock()
        self.topbar.update_view(v, now)
        self.strip.update_view(v, self.current)
        self.band.update_view(v)
        self.ledger.update_view(v)
        self.your_data.update_view(v.with_(now=now))
        self.check.update_view(v)
        self.settings.update_view(v.with_(now=now))
        self.m13.update_view(v)
        head = getattr(self.stage_widget, "head", None)
        if hasattr(self.stage_widget, "update_view"):
            self.stage_widget.update_view(v)
        elif head is not None:
            head.dataline.update_view(v.saved_progress, v.data_notes)
        self.stage_area.fit()
        if self.model is not None and self.bridge.runner.running:
            self.strip.set_run_fractions({sid: self.model.stage_fraction(sid) for sid in self.model.owners()})

    def _refresh_saved(self):
        self.topbar.update_view(self.view, self.clock())

    # Commands

    def open_guide(self):
        from wholecount.ui.widgets.guide import GuideDialog

        self.guide = GuideDialog(self)
        self.guide.open()
        return self.guide

    def bridge_undo(self):
        self.bridge.undo()

    def change_reviewer(self, name=None):
        msg = ReviewerDialog(self).run(name)
        self.last_reviewer_refusal = msg
        return msg

    def acknowledge_low(self):
        from wholecount.session.commands import AcknowledgeLowConfidence

        self.bridge.dispatch(AcknowledgeLowConfidence())

    def toggle_saved(self, on):
        if not on:
            if not self.confirm(copy.get("data.saved.title"), (copy.get("data.saved.confirm_off"),),
                                copy.get("data.saved.turn_off"), copy.get("close.keep")):
                self.refresh()
                return False
        self.bridge.set_saved_progress(on)
        return True

    # Jobs

    def start_job(self, job):
        if not self.bridge.start_job(job):
            return False
        self.model = ProgressModel(job.action_id)
        if hasattr(self.stage_widget, "job_started"):
            self.stage_widget.job_started(self.model)
        self.ticker.start()
        self.run_hold.hold()
        self.strip.set_run_fractions({sid: 0.0 for sid in self.model.owners()})
        self.refresh()
        return True

    def _step_begun(self, step, index, count, total, unit):
        if self.model.index_of(step) is None:
            return
        self.model.begin(step, total)
        a11y.announce(copy.get(f"progress.step.{step.value}"))
        self._show_progress()

    def _progressed(self, snap):
        if self.model is None or snap.step is None:
            return
        self.model.progress(snap.step, snap.done, snap.total, snap.message)
        self._show_progress()

    def _step_ended(self, step, found, seconds):
        self.model.end(step, found, seconds)
        self._show_progress()

    def _show_progress(self):
        self.ticker.show_progress(self.model)
        if hasattr(self.stage_widget, "job_progress"):
            self.stage_widget.job_progress(self.model)
        self.strip.set_run_fractions({sid: self.model.stage_fraction(sid) for sid in self.model.owners()})
        if self.dropdown.isVisible() and hasattr(self.dropdown.content, "show_model"):
            self.dropdown.content.show_model(self.model)

    # Actions the stage bodies start (M11)

    def add_files(self, paths):
        from wholecount.ui.jobs.actions import AddFilesJob

        s = self.bridge.session
        if s is None or self.run_hold.active:
            return False
        refused = [p for p in paths if str(p).startswith("\\\\") or str(p).startswith("//")]
        paths = [p for p in paths if p not in refused]
        msgs = [("src.drop.network_address", {})] if refused else []
        known = {pathlib.Path(p).name for p in s.setup.paths()}
        msgs += [("src.already_added", {"name": p.name}) for p in paths if p.name in known]
        paths = [p for p in paths if p.name not in known]
        self.bridge.ui["add_messages"] = tuple(msgs)
        if not paths:
            self.refresh()
            return False
        return self.start_job(AddFilesJob(s, paths, self.bridge.ui))

    def use_example_data(self, paths):
        from wholecount.session.frame import sample_backend
        from wholecount.session.commands import UseExampleData

        if self.run_hold.active or self.bridge.session is None:
            return
        self.bridge.ui["example_loaded"] = True
        self.bridge.ui["practice"] = True
        self.bridge.dispatch(UseExampleData(paths, sample_backend()))

    def start_process(self, then=None):
        from wholecount.ui.jobs.actions import ProcessJob

        if self.bridge.session is None:
            return False
        self._after_job = then
        return self.start_job(ProcessJob(self.bridge.session))

    def show_data(self, table_key):
        self.preview.show_table(table_key)
        self.preview.open_()

    def resume(self, entry, paths=None):
        """Add the same files again; they are matched by their contents, because no rows are saved (SPEC 10.2)."""
        from PySide6.QtWidgets import QFileDialog

        from wholecount.ui.jobs.actions import ResumeJob

        if self.run_hold.active or self.bridge.session is None:
            return False
        if paths is None:
            picked, _ = QFileDialog.getOpenFileNames(self, copy.get("src.resume_pick"), "", copy.get("src.drop.filter"))
            paths = [pathlib.Path(p) for p in picked]
        if not paths:
            return False

        def done(plan):
            self.bridge.ui["resume_plan"] = plan
        return self.start_job(ResumeJob(self.bridge.store(), entry, paths, done))

    def delete_saved(self, entry):
        self.bridge.delete_saved(entry)
        self.refresh()

    def _stage_job_ended(self, how, code=None, step=None):
        if hasattr(self.stage_widget, "job_ended"):
            self.stage_widget.job_ended(how, code, step)

    def _ask_text(self, title, prompt):
        from PySide6.QtWidgets import QInputDialog, QLineEdit

        text, ok = QInputDialog.getText(self, title, prompt, QLineEdit.Normal, "")
        return text.strip() if ok else None

    def fix_mapping_and_run(self, diag):
        """Match it and process again: the mapping change, then a run. Decisions come back by record key (A-07)."""
        from wholecount.session.commands import SetupChange
        from wholecount.session.survey import survey

        t = survey(self.bridge.session).table(diag.table_key)
        self.bridge.dispatch(SetupChange("mappings", (t.file_name, t.idx, diag.field), diag.column_better))
        return self.start_process()

    def open_queue(self, status):
        """Fix problems, step 2, on one status tab."""
        self.queue_request = status
        self.go_to("review")

    def _job_over(self):
        self.run_hold.release()
        self.strip.set_run_fractions(None)
        self.bridge.job_ended()

    def _finished(self, outcome):
        self.ticker.finished(outcome, self.view.saved_progress)
        self._stage_job_ended("finished")
        self._job_over()
        then, self._after_job = self._after_job, None
        if then:
            self.go_to(then)
        a11y.announce(self.ticker.left.text())

    def _cancelled(self):
        self.ticker.cancelled()
        self._stage_job_ended("cancelled")
        self._job_over()
        a11y.announce(self.ticker.left.text())

    def _failed(self, code, step):
        name = copy.get(f"progress.step.{step.value}") if step is not None else copy.get("action.process")
        self.ticker.failed(name, code)
        self._stage_job_ended("failed", code, step)
        self._job_over()
        a11y.announce(self.ticker.left.text())

    def _dropdown_pos(self):
        p = self.ticker.mapTo(self.centralWidget(), self.ticker.rect().bottomRight())
        x = max(20, p.x() - min(560, self.width() - 40) - 20)
        return x, p.y() + 1

    def toggle_steps(self):
        if self.dropdown.isVisible():
            self.dropdown.close_()
            return
        if self.model is None:
            return
        self.dropdown.set_content(steplist_for(self.model))
        self.dropdown.open_at(*self._dropdown_pos(), by_keyboard=self.ticker.all_button.hasFocus())

    def toggle_log(self):
        if self.dropdown.isVisible():
            self.dropdown.close_()
            return
        if self.model is None:
            return
        self.dropdown.set_content(LogView(self.model))
        self.dropdown.open_at(*self._dropdown_pos(), by_keyboard=self.ticker.log_button.hasFocus())

    # Close and Start over

    def request_close(self):
        self.close_requests += 1
        self.close()

    def closeEvent(self, ev):
        v = self.view
        running = self.bridge.runner.running
        lines = close_lines(bool(v.files), v.saved_progress, running)
        if lines and not self.closing_confirmed:
            if not self.confirm(copy.get("close.title"), lines, copy.get("top.close"), copy.get("close.keep")):
                ev.ignore()
                return
        if running:
            self.bridge.cancel_job()
            self.bridge.runner.wait()
        self.closing_confirmed = True
        self.bridge.release()
        ev.accept()

    def request_start_over(self):
        if not self.confirm(copy.get("start.title"), start_over_lines(), copy.get("start.button"), copy.get("close.keep")):
            return False
        self._start_over()
        self.ticker.reset()
        self.model = None
        self.go_to("sources")
        return True
