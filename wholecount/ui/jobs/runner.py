"""JobRunner: one worker QThread at a time (SPEC 11.6.1, 11.6.3).

A Job's run(sink) works on the worker and never touches the session or Qt. Its apply(session, result) runs on the main
thread inside one command, so one Undo takes back the whole job. A cancelled job drops its result, so the session is just
as it was. A job that raises shows a step name and an error code. The exception's message is never shown or logged, because
libraries put cell values in them (H8).
"""
import hashlib
import os
import time
import traceback
from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from wholecount.ui.jobs.sink import HEARTBEAT, QtProgressSink

RUN_LOG = []                              # in memory only (H9): (code, type name, ((file, function, line), ...))


def _frames(exc):
    return tuple((os.path.basename(f.filename), f.name, f.lineno) for f in traceback.extract_tb(exc.__traceback__))


def error_code(exc):
    """E- and six hex characters from the exception type and where it was raised. Never from its message."""
    frames = _frames(exc)
    where = frames[-1] if frames else ("", "", 0)
    raw = f"{type(exc).__name__}|{where[0]}|{where[2]}"
    return "E-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6].upper()


def log_failure(exc):
    code = error_code(exc)
    RUN_LOG.append((code, type(exc).__name__, _frames(exc)))
    return code


@dataclass(frozen=True)
class JobOutcome:
    action_id: str
    seconds: float
    steps: int


class _Worker(QObject):
    begun = Signal(object, int, str)      # Step, total, unit value
    posted = Signal(object)               # Snapshot
    ended = Signal(object, object, float)  # Step, ProgressMessage, seconds
    done = Signal()

    def __init__(self, job, clock):
        super().__init__()
        self.job = job
        self.result = None
        self.error = None
        self.sink = QtProgressSink(self.posted.emit, lambda s, t, u: self.begun.emit(s, t, u.value),
                                   lambda s, f, sec: self.ended.emit(s, f, sec), clock)

    @Slot()
    def run(self):
        try:
            self.result = self.job.run(self.sink)
        except Exception as exc:          # noqa: BLE001  the job's failure is shown as a code, never its message
            self.error = exc
        self.done.emit()


class JobRunner(QObject):
    step_begun = Signal(object, int, int, int, str)   # Step, index, count, total, unit
    progressed = Signal(object)
    step_ended = Signal(object, object, float)
    finished = Signal(object)                         # JobOutcome
    cancelled = Signal()
    failed = Signal(str, object)                      # error code, the Step it failed in (or None)

    def __init__(self, parent=None, apply=None, clock=time.monotonic):
        super().__init__(parent)
        self._apply = apply
        self._clock = clock
        self._thread = None
        self._worker = None
        self._job = None
        self._index = -1
        self._current_step = None
        self._started = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(int(HEARTBEAT * 1000))
        self._timer.timeout.connect(self._heartbeat)
        self.threads_started = 0

    @property
    def running(self):
        return self._thread is not None

    @property
    def job(self):
        return self._job

    def start(self, job):
        if self.running:
            return False
        self._job = job
        self._index = -1
        self._current_step = None
        self._started = self._clock()
        self._thread = QThread()
        self._worker = _Worker(job, self._clock)
        self._worker.moveToThread(self._thread)
        self._worker.begun.connect(self._on_begun)
        self._worker.posted.connect(self.progressed)
        self._worker.ended.connect(self.step_ended)
        self._worker.done.connect(self._on_done)
        self._thread.started.connect(self._worker.run)
        self.threads_started += 1
        self._thread.start()
        self._timer.start()
        return True

    def cancel(self):
        if self._worker is not None:
            self._worker.sink.cancel()

    def wait(self, ms=10000):
        """For Close and tests: block until the worker returns, then deliver its result on this thread."""
        from PySide6.QtCore import QCoreApplication, QDeadlineTimer

        deadline = QDeadlineTimer(ms)
        while self.running and not deadline.hasExpired():
            QCoreApplication.processEvents()
            QThread.msleep(2)

    def _heartbeat(self):
        if self._worker is not None:
            self._worker.sink.heartbeat()

    def _on_begun(self, step, total, unit):
        self._index += 1
        self._current_step = step
        self.step_begun.emit(step, self._index, len(self._job.steps), total, unit)

    def _cleanup(self):
        self._timer.stop()
        t, w = self._thread, self._worker
        self._thread = self._worker = None
        t.quit()
        t.wait()
        w.deleteLater()
        t.deleteLater()

    def _on_done(self):
        w, job = self._worker, self._job
        seconds = round(self._clock() - self._started, 1)
        cancelled = w.sink.cancelled()
        error, result = w.error, w.result
        step = self._current_step
        self._cleanup()
        self._job = None
        if error is not None:
            self.failed.emit(log_failure(error), step)
            return
        if cancelled:
            self.cancelled.emit()
            return
        try:
            if self._apply is not None:
                self._apply(job, result)
        except Exception as exc:          # noqa: BLE001
            self.failed.emit(log_failure(exc), step)
            return
        self.finished.emit(JobOutcome(job.action_id, seconds, len(job.steps)))


def snapshot_with_elapsed(snap, elapsed):
    return replace(snap, elapsed=elapsed)
