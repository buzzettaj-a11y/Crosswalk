"""SessionBridge: the only thing the UI uses to touch the session (SPEC 3.2, 3.4, 8.5).

dispatch, undo and start_job. It emits `changed` after a command or undo has re-derived everything downstream, and
`stale_changed`. Widgets redraw from a fresh FrameView on `changed`, never from partial state.
"""
from PySide6.QtCore import QObject, Signal

from wholecount.ui.frame.view import FrameView, build_view
from wholecount.session.commands import JobCommand
from wholecount.ui.jobs.runner import JobRunner


class SessionBridge(QObject):
    changed = Signal()
    stale_changed = Signal(object)
    refused = Signal(str)

    def __init__(self, session=None, ui=None, preflight=None, clock=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.ui = dict(ui or {})
        self.preflight = preflight
        self.clock = clock
        self.runner = JobRunner(self, apply=self._apply_job)
        self.runner.finished.connect(self._job_finished)
        self._last_stale = frozenset()
        self._last_view = None
        self.dispatched = []

    def view(self):
        if self.session is None:
            return self._last_view or FrameView()
        v = build_view(self.session, self.ui, self.preflight, self.clock)
        v = v.with_(running=self.runner.running) if self.runner.running != v.running else v
        self._last_view = v
        return v

    def _changed(self):
        v = self.view()
        if v.stale != self._last_stale:
            self._last_stale = v.stale
            self.stale_changed.emit(v.stale)
        self.changed.emit()

    def dispatch(self, command):
        from wholecount.session.commands import CommandResult, Refused
        from wholecount.session.reviewer import BadReviewerName

        self.dispatched.append(command)
        try:
            result = self.session.history.execute(command)
        except (Refused, BadReviewerName) as exc:
            self.refused.emit(exc.code)
            return CommandResult(ok=False)
        self._after_command(command)
        self._changed()
        return result

    def _after_command(self, command):
        from wholecount.session.commands import SetReviewer

        if isinstance(command, SetReviewer):
            self.ui["reviewer_asked"] = True
        if self.session.store is not None and self.ui.get("saved_progress", True):
            self.ui["saved_at"] = self.session.clock()

    def undo(self):
        label = self.session.history.undo()
        self._changed()
        return label

    def start_job(self, job):
        ok = self.runner.start(job)
        if ok:
            self.ui["running"] = True
            self.changed.emit()
        return ok

    def cancel_job(self):
        self.runner.cancel()

    def job_ended(self):
        self.ui["running"] = False
        self._changed()

    def _apply_job(self, job, result):
        self.session.history.execute(JobCommand(job, result))

    def _job_finished(self, outcome):
        if outcome.action_id == "process":
            self.ui["run_seconds"] = outcome.seconds

    def start_over(self):
        """Clear the batch from memory and delete its saved progress (SPEC 11.3). Downloaded files are never touched."""
        from wholecount.session.state import Session

        old = self.session
        if old is None:
            return
        if old.store is not None:
            path = old.store.sessions / f"{old.session_id}.wcs"
            if path.exists():
                path.unlink()
        fresh = Session(old.secret, backend=old.backend, districts=old.districts, clock=old.clock, today=old.today,
                        allow_sample=old.allow_sample)
        fresh.store = old.store
        self.session = fresh
        for k in ("running", "run_seconds", "downloaded", "saved_at", "reviewer_asked", "steps_continued", "map_confirmed"):
            self.ui.pop(k, None)
        self._changed()

    def release(self):
        """On close: let go of the session, so nothing about the batch stays referenced by the window."""
        self.session = None

    def set_saved_progress(self, on):
        self.ui["saved_progress"] = bool(on)
        store = self.session.store if self.session is not None else None
        if store is not None:
            store.set_saved_progress(on, None)
        self._changed()


class StaticBridge(SessionBridge):
    """A bridge over a fixed FrameView, for the frame tests and make screens. Commands are recorded, never run."""

    def __init__(self, view=None, parent=None):
        super().__init__(None, parent=parent)
        self.fixed = view or FrameView()
        self.undo_calls = 0
        self.saved_progress_calls = []

    def view(self):
        return self.fixed.with_(running=self.runner.running or self.fixed.running)

    def set_view(self, view):
        self.fixed = view
        self._changed()

    def dispatch(self, command):
        from wholecount.session.commands import CommandResult

        self.dispatched.append(command)
        self.changed.emit()
        return CommandResult()

    def undo(self):
        self.undo_calls += 1
        self.changed.emit()
        return None

    def job_ended(self):
        self.changed.emit()

    def _apply_job(self, job, result):
        job.apply(None, result)

    def start_over(self):
        self.start_over_calls = getattr(self, "start_over_calls", 0) + 1
        self.fixed = FrameView(saved_progress=self.fixed.saved_progress, now=self.fixed.now, backend=self.fixed.backend,
                               release=self.fixed.release, checks=self.fixed.checks)
        self._changed()

    def set_saved_progress(self, on):
        self.saved_progress_calls.append(bool(on))
        self.fixed = self.fixed.with_(saved_progress=bool(on))
        self._changed()
