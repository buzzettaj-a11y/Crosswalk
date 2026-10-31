"""stage_state and stage_caption for all nine stages (SPEC 11.3, 10.4). They read only FrameView.

A caption is data: a copy ID and int parameters. A fixed phrase appears only when there's nothing to count.
"""
from dataclasses import dataclass, field

from wholecount import copy

CURRENT, DONE, NOTHING, LATER = "current", "done", "nothing", "later"


@dataclass(frozen=True)
class Caption:
    parts: tuple                          # ((copy ID, params, tone), ...) drawn in order on one line
    stale: bool = False

    @property
    def text(self):
        return "".join(copy.get(k, **p) for k, p, _ in self.parts)

    @property
    def tone(self):
        return "amber" if self.stale else self.parts[0][2]


def _c(key, tone=None, **params):
    return (key, params, tone)


def _state(stage_id, v):
    if stage_id == "sources":
        return DONE if v.tables else LATER
    if stage_id == "schema":
        return DONE if v.schema_custom else NOTHING
    if stage_id == "prepare":
        return DONE if v.steps_proposed else NOTHING
    if stage_id == "map":
        return DONE if v.map_tables and v.map_confirmed >= v.map_tables else LATER
    if stage_id == "programs":
        if not v.program_files and v.has_run and not v.program_names:
            return NOTHING
        return DONE if v.program_names and not v.program_groups_open else LATER
    if stage_id == "run":
        return DONE if v.has_run else LATER
    if stage_id == "review":
        if not v.has_run:
            return LATER
        return DONE if v.review_finished or v.rows_open == 0 else LATER
    if stage_id == "summary":
        return DONE if v.is_final else LATER
    if stage_id == "export":
        return DONE if v.downloaded else LATER
    raise KeyError(stage_id)


def stage_state(stage_id, view, current=None):
    """current, done, nothing or later. Current wins. Stale is separate (stage_caption sets it)."""
    if current == stage_id:
        return CURRENT
    return _state(stage_id, view)


def _parts(stage_id, v):
    if stage_id == "sources":
        return (_c("strip.cap.sources_none"),) if not v.files else (_c("strip.cap.sources", files=v.files, tables=v.tables),)
    if stage_id == "schema":
        return (_c("strip.cap.schema_custom", n=v.schema_custom),) if v.schema_custom else (_c("strip.cap.schema_default"),)
    if stage_id == "prepare":
        if not v.steps_proposed:
            return (_c("strip.cap.prepare_none"),)
        head = (_c("strip.cap.prepare_kept", n=v.steps_kept) if v.steps_continued
                else _c("strip.cap.prepare_proposed", n=v.steps_proposed))
        return (head, _c("strip.cap.prepare_noop", "amber", m=v.steps_noop)) if v.steps_noop else (head,)
    if stage_id == "map":
        head = _c("strip.cap.map", m=v.map_confirmed, t=v.map_tables)
        return (head, _c("strip.cap.map_wrong", "blue", k=v.map_wrong)) if v.map_wrong else (head,)
    if stage_id == "programs":
        if v.has_run and not v.program_files and not v.program_names:
            return (_c("strip.cap.programs_none"),)
        if v.program_groups_open:
            return (_c("strip.cap.programs_open", n=v.program_groups_open),)
        if v.program_names:
            return (_c("strip.cap.programs_done", n=v.programs_counted),)
        return (_c("strip.cap.programs_none"),) if v.has_run else (_c("strip.cap.not_run"),)
    if stage_id == "run":
        if v.running:
            return (_c("strip.cap.run_running"),)
        if v.has_run and v.run_seconds is not None:
            return (_c("strip.cap.run_done", secs=f"{v.run_seconds:.1f}"),)
        return (_c("strip.cap.run_ready"),)
    if not v.has_run:
        return (_c("strip.cap.not_run"),)
    if stage_id == "review":
        return (_c("strip.cap.review_open", n=v.rows_open),) if v.rows_open else (_c("strip.cap.review_done"),)
    if stage_id == "summary":
        c = v.counts
        if c is None:
            return (_c("strip.cap.not_run"),)
        if c.open_pairs or c.open_copy_groups:
            head = _c("strip.cap.summary_pairs", n=c.open_pairs)
            return (head, _c("strip.cap.summary_groups", g=c.open_copy_groups)) if c.open_copy_groups else (head,)
        if c.not_counted_yet:
            return (_c("strip.cap.summary_not_counted", k=c.not_counted_yet),)
        return (_c("strip.cap.summary_final"),) if c.is_final else (_c("strip.cap.summary_not_counted", k=0),)
    if stage_id == "export":
        if v.confidence is not None and v.confidence.level == "low" and not v.confidence.acknowledged:
            return (_c("strip.cap.export_held"),)
        return (_c("strip.cap.export_ready", n=v.files_ready),)
    raise KeyError(stage_id)


def stage_caption(stage_id, view):
    """The strip caption. A stale stage says only `out of date` and never a count."""
    if stage_id in view.stale:
        return Caption((_c("strip.cap.stale", "amber"),), stale=True)
    return Caption(_parts(stage_id, view))
