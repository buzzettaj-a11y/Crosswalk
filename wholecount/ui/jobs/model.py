"""ProgressModel, on the GUI side (SPEC 11.6.3). Counts, totals and fractions only move forward."""
from dataclasses import dataclass

from wholecount.ui.jobs.steps import steps_of, weights


@dataclass
class StepState:
    total: int = 0
    done: int = 0
    begun: bool = False
    ended: bool = False
    seconds: float | None = None
    message: object = None                # the latest ProgressMessage
    found: object = None                  # the closing ProgressMessage

    @property
    def fraction(self):
        if self.ended:
            return 1.0
        if not self.total:
            return 0.0
        return min(1.0, self.done / self.total)


class ProgressModel:
    def __init__(self, action_id):
        self.action_id = action_id
        self.steps = steps_of(action_id)
        self.weights = weights(action_id)
        self.states = [StepState() for _ in self.steps]
        self.current = -1
        self._overall = 0.0
        self._stage = {}

    def index_of(self, step):
        """The first unfinished row for this step, else its last row, else None for a step this action doesn't list."""
        for i, s in enumerate(self.steps):
            if s.step == step and not self.states[i].ended:
                return i
        hits = [i for i, s in enumerate(self.steps) if s.step == step]
        return hits[-1] if hits else None

    def begin(self, step, total):
        i = self.index_of(step)
        if i is None:
            return
        self.current = max(self.current, i)
        st = self.states[i]
        st.begun = True
        st.total = max(st.total, int(total))

    def progress(self, step, done, total, message=None):
        i = self.index_of(step)
        if i is None:
            return
        st = self.states[i]
        st.begun = True
        st.total = max(st.total, int(total), int(done))
        st.done = max(st.done, min(int(done), st.total))
        if message is not None:
            st.message = message

    def end(self, step, found, seconds):
        i = self.index_of(step)
        if i is None:
            return
        st = self.states[i]
        st.begun = True
        st.done = st.total
        st.ended = True
        st.found = found
        st.seconds = round(seconds, 1)

    def overall_fraction(self):
        f = sum(w * s.fraction for w, s in zip(self.weights, self.states))
        self._overall = max(self._overall, min(1.0, f))
        return self._overall

    def stage_fraction(self, stage_id):
        idx = [i for i, s in enumerate(self.steps) if s.owner == stage_id]
        if not idx:
            return None
        tw = sum(self.weights[i] for i in idx)
        f = sum(self.weights[i] * self.states[i].fraction for i in idx) / tw
        self._stage[stage_id] = max(self._stage.get(stage_id, 0.0), f)
        return self._stage[stage_id]

    def owners(self):
        return {s.owner for s in self.steps if s.owner}

    @property
    def total_seconds(self):
        return round(sum(s.seconds or 0 for s in self.states), 1)
