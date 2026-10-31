"""Progress types (SPEC 11.6.3, H8, H14). These are the only definitions: later milestones import them and never add a second step list.

A ProgressMessage holds a copy registry ID and parameters of three types only: SourceRef, StepRef and int. It can't hold a free
string, so a client value can never reach the progress line or a log.
"""
import enum
from dataclasses import dataclass, field


class Step(enum.Enum):
    """The 16 distinct step names in SPEC 11.6.2. The value is the copy registry key under progress.step."""

    READING_FILES = "reading_files"
    FINDING_TABLES = "finding_tables"
    TIDYING_UP = "tidying_up"
    CHECKING_EVERY_ROW = "checking_every_row"
    PLACING_ADDRESSES = "placing_addresses"
    FINDING_COPIES = "finding_copies"
    MATCHING_PEOPLE = "matching_people"
    COUNTING_AND_BALANCING = "counting_and_balancing"
    COUNTING = "counting"
    LOOKING_UP_ADDRESSES = "looking_up_addresses"
    WRITING_FILES = "writing_files"
    REAPPLYING_DECISIONS = "reapplying_decisions"
    READING_CORRECTIONS = "reading_corrections"
    CHECKING_SIGNATURES = "checking_signatures"
    DRAWING_PAIRS = "drawing_pairs"
    PROTECTING_BACKUP = "protecting_backup"


class Unit(enum.Enum):
    """What a step's count counts."""

    FILES = "files"
    ROWS = "rows"
    ADDRESSES = "addresses"
    PAIRS = "pairs"
    DECISIONS = "decisions"


@dataclass(frozen=True)
class SourceRef:
    """A file as the operator sees it: its letter and its file name. File names may appear on screen (H8), never cell values."""

    letter: str
    file_name: str

    def __post_init__(self):
        if not isinstance(self.letter, str) or not self.letter.isalpha() or not self.letter.isupper():
            raise TypeError("letter must be an uppercase source letter")
        if not isinstance(self.file_name, str):
            raise TypeError("file_name must be a str")


@dataclass(frozen=True)
class StepRef:
    step: Step

    def __post_init__(self):
        if not isinstance(self.step, Step):
            raise TypeError("step must be a Step")


_ALLOWED = (SourceRef, StepRef)


@dataclass(frozen=True)
class ProgressMessage:
    message_id: str
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.message_id, str):
            raise TypeError("message_id must be a str")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dict")
        for name, value in self.params.items():
            if not isinstance(name, str):
                raise TypeError("parameter names must be str")
            if isinstance(value, bool) or not isinstance(value, (int, *_ALLOWED)):
                raise TypeError(f"parameter {name} must be a SourceRef, StepRef or int")
        # A frozen copy, so the caller can't change the message after it's checked.
        object.__setattr__(self, "params", dict(self.params))


class ProgressSink:
    """What the engine reports progress to. The UI implements it in M10."""

    def begin(self, step_id, total, unit):
        raise NotImplementedError

    def advance(self, n, message):
        raise NotImplementedError

    def end(self, found):
        raise NotImplementedError

    def cancelled(self):
        raise NotImplementedError


class NullSink(ProgressSink):
    def begin(self, step_id, total, unit):
        _check_begin(step_id, total, unit)

    def advance(self, n, message):
        _check_message(message)

    def end(self, found):
        _check_message(found)

    def cancelled(self):
        return False


class RecordingSink(ProgressSink):
    """Keeps every call, for tests. Each event is a tuple whose first item is the method name."""

    def __init__(self, cancel_after=None):
        self.events = []
        self._cancel_after = cancel_after

    def begin(self, step_id, total, unit):
        _check_begin(step_id, total, unit)
        self.events.append(("begin", step_id, total, unit))

    def advance(self, n, message):
        _check_message(message)
        self.events.append(("advance", n, message))

    def end(self, found):
        _check_message(found)
        self.events.append(("end", found))

    def cancelled(self):
        return self._cancel_after is not None and len(self.events) >= self._cancel_after

    def messages(self):
        return [e[-1] for e in self.events if e[0] in ("advance", "end")]


def _check_begin(step_id, total, unit):
    if not isinstance(step_id, Step) or not isinstance(unit, Unit):
        raise TypeError("begin takes a Step and a Unit")
    if isinstance(total, bool) or not isinstance(total, int):
        raise TypeError("total must be an int")


def _check_message(message):
    if not isinstance(message, ProgressMessage):
        raise TypeError("expected a ProgressMessage")


def _render_value(value):
    from wholecount import copy

    if isinstance(value, SourceRef):
        return f"[{value.letter}] {value.file_name}"
    if isinstance(value, StepRef):
        return copy.get(f"progress.step.{value.step.value}")
    return value


def render(message):
    """The message's text from the copy registry, with its parameters filled in."""
    from wholecount import copy

    _check_message(message)
    return copy.get(message.message_id, **{k: _render_value(v) for k, v in message.params.items()})
