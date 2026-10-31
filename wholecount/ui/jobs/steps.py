"""The nine action step lists of SPEC 11.6.2, as data. Every step is a member of M01's Step enum, so there's one list.

Weights for Process come from the prototype's measured log (30.5 s in all). The other actions have no measured log, so
their steps carry equal weights. Weights are normalized to sum to 1 inside each action.
"""
from dataclasses import dataclass

from wholecount.session.progress import Step, Unit


@dataclass(frozen=True)
class StepDef:
    short: str
    step: Step
    unit: Unit
    owner: str | None                     # the stage whose strip underline fills, or None

    @property
    def name_id(self):
        return f"progress.step.{self.step.value}"


STEPS = {s.short: s for s in (
    StepDef("read", Step.READING_FILES, Unit.FILES, "run"),
    StepDef("tables", Step.FINDING_TABLES, Unit.TABLES, "run"),
    StepDef("tidy", Step.TIDYING_UP, Unit.ROWS, "prepare"),
    StepDef("check", Step.CHECKING_EVERY_ROW, Unit.ROWS, "run"),
    StepDef("place", Step.PLACING_ADDRESSES, Unit.ADDRESSES, "run"),
    StepDef("copies", Step.FINDING_COPIES, Unit.ROWS, "review"),
    StepDef("people", Step.MATCHING_PEOPLE, Unit.ROWS, "summary"),
    StepDef("count_balance", Step.COUNTING_AND_BALANCING, Unit.CHECKS, "summary"),
    StepDef("count", Step.COUNTING, Unit.ROWS, "summary"),
    StepDef("lookup", Step.LOOKING_UP_ADDRESSES, Unit.ADDRESSES, "run"),
    StepDef("write", Step.WRITING_FILES, Unit.FILES, "export"),
    StepDef("reapply", Step.REAPPLYING_DECISIONS, Unit.DECISIONS, "review"),
    StepDef("corr_read", Step.READING_CORRECTIONS, Unit.ROWS, "review"),
    StepDef("corr_check", Step.CHECKING_SIGNATURES, Unit.CHECKS, "review"),
    StepDef("draw", Step.DRAWING_PAIRS, Unit.PAIRS, None),
    StepDef("protect", Step.PROTECTING_BACKUP, Unit.FILES, None),
)}

BY_STEP = {s.step: s for s in STEPS.values()}

# (short ID, raw weight). Process weights are the prototype's measured seconds.
ACTIONS = {
    "add_files": (("read", 1), ("tables", 1)),
    "process": (("read", 2.1), ("tidy", 1.4), ("check", 3.0), ("place", 18.6), ("copies", 0.9), ("people", 4.2),
                ("count_balance", 0.3)),
    "preview": (("check", 1), ("people", 1), ("count", 1)),
    "look_up": (("lookup", 1),),
    "download": (("write", 1),),
    "resume": (("read", 1), ("reapply", 1)),
    "corrections": (("corr_read", 1), ("corr_check", 1), ("reapply", 1)),
    "calibrate": (("people", 1), ("draw", 1)),
    "backup": (("protect", 1),),
}


def steps_of(action_id):
    return tuple(STEPS[s] for s, _ in ACTIONS[action_id])


def weights(action_id):
    raw = ACTIONS[action_id]
    total = sum(w for _, w in raw)
    return tuple(w / total for _, w in raw)
