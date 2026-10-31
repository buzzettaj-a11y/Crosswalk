"""STAGES, the one list of stages (SPEC 1, A-19, A-21). Everything that shows a stage name or number reads it."""
from dataclasses import dataclass

from wholecount import copy


@dataclass(frozen=True)
class Stage:
    id: str
    number: int

    @property
    def technical(self):
        return copy.get(f"stage.{self.id}.technical")

    @property
    def plain(self):
        return copy.get(f"stage.{self.id}.name")

    @property
    def subtitle_id(self):
        return f"stage.{self.id}.subtitle"

    @property
    def nn(self):
        return f"{self.number:02d}"


IDS = ("sources", "schema", "prepare", "map", "programs", "run", "review", "summary", "export")
STAGES = tuple(Stage(sid, i + 1) for i, sid in enumerate(IDS))
BY_ID = {s.id: s for s in STAGES}


def total():
    return f"{len(STAGES):02d}"


def kicker(stage_id):
    s = BY_ID[stage_id]
    return copy.get("stage.kicker", number=s.nn, total=total(), technical=s.technical)


def strip_kicker(stage_id):
    s = BY_ID[stage_id]
    return copy.get("stage.strip_kicker", number=s.nn, technical=s.technical)
