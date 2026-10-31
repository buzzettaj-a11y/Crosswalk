"""QtProgressSink: the engine's ProgressSink for the worker thread (SPEC 11.6.3).

advance stores the latest state under a lock and posts a snapshot when 100 ms have passed since the last post. The runner
re-posts the latest snapshot on a 250 ms timer when nothing was posted, so a quiet step still updates. Only ints, Step
members and ProgressMessage cross to the GUI thread (H8).
"""
import threading
import time
from dataclasses import dataclass, replace

from wholecount.session.progress import ProgressSink, _check_begin, _check_message

POST_EVERY = 0.100
HEARTBEAT = 0.250


@dataclass(frozen=True)
class Snapshot:
    step: object                          # Step
    done: int
    total: int
    message: object                       # ProgressMessage or None
    elapsed: float


class QtProgressSink(ProgressSink):
    def __init__(self, post, begun=None, ended=None, clock=time.monotonic):
        self._post = post                 # callable(Snapshot), thread safe (a queued signal emit)
        self._begun = begun or (lambda step, total, unit: None)
        self._ended = ended or (lambda step, found, seconds: None)
        self._clock = clock
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._last_post = None
        self._latest = None
        self._step = None
        self._step_start = None
        self._done = 0
        self._total = 0
        self._start = clock()
        self.posts = 0

    def cancel(self):
        self._cancel.set()

    def cancelled(self):
        return self._cancel.is_set()

    def begin(self, step_id, total, unit):
        _check_begin(step_id, total, unit)
        with self._lock:
            self._step, self._total, self._done = step_id, total, 0
            self._step_start = self._clock()
            self._latest = Snapshot(step_id, 0, total, None, self._clock() - self._start)
        self._begun(step_id, total, unit)
        self._emit(force=True)

    def advance(self, n, message):
        _check_message(message)
        with self._lock:
            self._done = min(self._total, self._done + int(n)) if self._total else self._done + int(n)
            self._latest = Snapshot(self._step, self._done, max(self._total, self._done), message, self._clock() - self._start)
        self._emit()

    def end(self, found):
        _check_message(found)
        with self._lock:
            step = self._step
            seconds = self._clock() - (self._step_start if self._step_start is not None else self._start)
            self._latest = Snapshot(step, max(self._total, self._done), max(self._total, self._done), found,
                                    self._clock() - self._start)
        self._emit(force=True)
        self._ended(step, found, seconds)

    def heartbeat(self):
        """Called by the runner's timer on the GUI thread: re-post the latest snapshot if nothing was posted lately."""
        with self._lock:
            due = self._latest is not None and (self._last_post is None or self._clock() - self._last_post >= HEARTBEAT)
        if due:
            with self._lock:
                self._latest = replace(self._latest, elapsed=self._clock() - self._start)
            self._emit(force=True)

    def _emit(self, force=False):
        with self._lock:
            now = self._clock()
            if not force and self._last_post is not None and now - self._last_post < POST_EVERY:
                return
            self._last_post = now
            snap = self._latest
            self.posts += 1
        if snap is not None:
            self._post(snap)
