"""FrameView: the frozen snapshot the frame draws from (SPEC 11.3). The UI reads the session only through build_view.

Tests build a FrameView directly, so most frame tests need no engine. Nothing here computes a rule. Counts, the balance,
the equations, the confidence level and its reason all come from the engine through the session.
"""
import datetime as dt
from dataclasses import dataclass, field, replace

from wholecount.session.frame import Locations

RESULT_STAGES = frozenset({"run", "review", "summary", "export"})


@dataclass(frozen=True)
class CountsView:
    received: int = 0
    counted: int = 0
    not_counted_yet: int = 0
    set_aside: int = 0
    goal1: tuple = (0, 0)                 # (low, high)
    goal2: tuple = (0, 0)
    open_pairs: int = 0
    open_copy_groups: int = 0
    is_final: bool = False                # the engine's COUNT-2, never worked out here
    locations: Locations = field(default_factory=Locations)
    balance_ok: bool = True
    lines: tuple = ()                     # ((copy ID, params), (copy ID, params)) from engine.counts.ledger_lines


@dataclass(frozen=True)
class ConfidenceView:
    level: str | None = None              # low, medium, high
    parts: tuple = ()                     # the engine's (code, params) reasons
    measures: tuple = ()                  # (name, numerator, denominator)
    thresholds: dict = field(default_factory=dict)
    calibration: tuple | None = None      # (date text, rates text), M13
    acknowledged: bool = False


@dataclass(frozen=True)
class PreviewView:
    goal1: int
    goal2: int
    taken_at: str                         # HH:MM, from the session clock
    stale: bool = False


@dataclass(frozen=True)
class CheckRow:
    check_id: str                         # copy key under check.row
    status: str                           # ok, warn, missing
    detail: tuple                         # (copy ID, params)


@dataclass(frozen=True)
class FrameView:
    practice: bool = False
    files: int = 0
    tables: int = 0
    rows_in: int = 0
    schema_custom: int = 0
    steps_proposed: int = 0
    steps_kept: int = 0
    steps_continued: bool = False
    steps_noop: int = 0
    steps_added: int = 0
    steps_removed: int = 0
    map_confirmed: int = 0
    map_tables: int = 0
    map_wrong: int = 0
    map_required: tuple = (0, 0)          # (set, total)
    program_files: int = 0
    program_names: int = 0
    programs_counted: int = 0
    program_groups_open: int = 0
    program_groups_confirmed: int = 0
    preview: PreviewView | None = None
    has_run: bool = False
    running: bool = False
    run_seconds: float | None = None
    rows_open: int = 0
    review_finished: bool = False
    files_ready: int = 0
    downloaded: bool = False
    stale: frozenset = frozenset()        # stage IDs whose results are out of date
    counts: CountsView | None = None
    confidence: ConfidenceView | None = None
    undo_label: tuple | None = None       # (copy ID, params) of the top command
    reviewer: str | None = None
    reviewer_asked: bool = False
    saved_progress: bool = True
    saved_at: dt.datetime | None = None
    now: dt.datetime | None = None
    backend: str = "none"                 # geosupport, reference, reference_sample, fake, none
    release: str = ""
    release_stale: bool = False
    checks: tuple = ()
    data_notes: tuple = ()                # copy IDs, filled only by M13

    @property
    def is_final(self):
        return self.counts is not None and self.counts.is_final

    @property
    def results_stale(self):
        return bool(self.stale & RESULT_STAGES)

    @property
    def can_place(self):
        return self.backend not in ("none",)

    def with_(self, **kw):
        return replace(self, **kw)


def _thresholds():
    from wholecount.settings.loader import load

    return dict(load("confidence")["batch"])


def counts_view(results):
    """CountsView from session Results. The balance check and the final flag are the engine's."""
    from wholecount.session import frame

    c = results.counts
    return CountsView(c.received, c.counted, c.not_counted_yet, c.set_aside, (c.goal1.low, c.goal1.high),
                      (c.goal2.low, c.goal2.high), c.open_pairs, c.open_copy_groups, c.final, c.locations, frame.balance_ok(results),
                      frame.lines(results))


def confidence_view(session):
    r = session.results
    conf = r.confidence
    acked = session.acknowledged is not None and session.acknowledged[0] == r.version
    return ConfidenceView(conf.level, conf.parts, conf.measures, _thresholds(), conf.calibration, acked)


def stale_stages(session):
    if session.results is None:
        return frozenset()
    return RESULT_STAGES if session.stale else frozenset()


def _default_schema_keys():
    from wholecount.session.frame import default_field_keys

    return default_field_keys()


def check_rows(pre, font_ok=True, secret_ok=True, store_ok=True, dpapi_ok=True, guard_ok=False, windows=""):
    """The system check table (SPEC 11.8). H8-safe: names, counts and states only, never a row."""
    rows = []
    if pre is None:
        rows.append(CheckRow("geosupport", "missing", ("check.detail.geosupport_none", {})))
    elif pre.release:
        rows.append(CheckRow("geosupport", "warn" if pre.release_stale else "ok",
                             ("check.detail.geosupport_old" if pre.release_stale else "check.detail.geosupport",
                              {"release": pre.release})))
    else:
        rows.append(CheckRow("geosupport", "missing", ("check.detail.geosupport_none", {})))
    kind = pre.reference_kind if pre is not None else "none"
    if kind == "real":
        ref = CheckRow("reference", "ok", ("check.detail.reference_real",
                                           {"file": getattr(pre.backend, "file_name", "") or "reference.csv",
                                            "n": pre.reference_rows}))
    elif kind == "sample":
        ref = CheckRow("reference", "warn", ("check.detail.reference_sample", {}))
    elif kind == "several_reference_files":
        ref = CheckRow("reference", "warn", ("check.detail.reference_several", {}))
    elif kind == "reference_unreadable":
        ref = CheckRow("reference", "warn", ("check.detail.reference_unreadable", {}))
    else:
        ref = CheckRow("reference", "missing", ("check.detail.reference_none", {}))
    rows.append(ref)
    n = pre.district_files if pre is not None else 0
    rows.append(CheckRow("districts", "ok" if n else "missing", ("check.detail.districts", {"n": n})))
    rows.append(CheckRow("secret", "ok" if secret_ok else "warn",
                         ("check.detail.secret_ok" if secret_ok else "check.detail.secret_missing", {})))
    rows.append(CheckRow("store", "ok" if store_ok else "warn",
                         ("check.detail.store_ok" if store_ok else "check.detail.store_bad", {})))
    rows.append(CheckRow("dpapi", "ok" if dpapi_ok else "warn",
                         ("check.detail.dpapi_ok" if dpapi_ok else "check.detail.dpapi_bad", {})))
    rows.append(CheckRow("font", "ok" if font_ok else "warn",
                         ("check.detail.font_ok" if font_ok else "check.detail.font_bad", {})))
    rows.append(CheckRow("guard", "ok" if guard_ok else "warn",
                         ("check.detail.guard_ok" if guard_ok else "check.detail.guard_off", {})))
    rows.append(CheckRow("windows", "ok" if windows else "warn", ("check.detail.windows", {"version": windows or "-"})))
    return tuple(rows)


def build_view(session, ui=None, preflight=None, clock=None):
    """The snapshot. `ui` carries window-side facts the session doesn't hold: running, the last run's seconds, whether a
    download happened, the saved-progress switch and when it last saved, and font and guard state."""
    from wholecount.session.frame import files_ready

    ui = ui or {}
    s = session
    r = s.results
    setup = s.setup
    files = len(setup.paths())
    included = [k for k, v in setup.sections["tables"].items() if v not in (False, None)]
    tables = len(r.works) if r is not None else len(included)
    schema_keys = {f.key for f in s.schema().enabled_fields()}
    steps = list(setup.sections["steps"].values())
    view = FrameView(
        practice=bool(r is not None and r.practice) or bool(ui.get("practice")),
        files=files, tables=tables,
        rows_in=r.counts.received if r is not None else 0,
        schema_custom=len(schema_keys - _default_schema_keys()),
        steps_proposed=len(steps), steps_kept=len(steps) if ui.get("steps_continued") else 0,
        steps_continued=bool(ui.get("steps_continued")),
        map_tables=tables, map_confirmed=int(ui.get("map_confirmed", 0)),
        has_run=r is not None, running=bool(ui.get("running")), run_seconds=ui.get("run_seconds"),
        rows_open=r.counts.not_counted_yet if r is not None else 0,
        review_finished=s.finished is not None,
        files_ready=files_ready(bool(r.practice)) if r is not None else 0,
        downloaded=bool(ui.get("downloaded")),
        stale=stale_stages(s),
        undo_label=(s.history.stack[-1].label.key, dict(s.history.stack[-1].label.params)) if s.history.stack else None,
        reviewer=s.reviewer or None, reviewer_asked=bool(ui.get("reviewer_asked", s.reviewer)),
        saved_progress=bool(ui.get("saved_progress", True)), saved_at=ui.get("saved_at"),
        now=(clock or s.clock)(),
        data_notes=tuple(ui.get("data_notes", ())),
    )
    if r is not None:
        program_cols = [v for v in setup.sections["program_columns"].values() if v]
        view = view.with_(program_files=len(program_cols), program_names=len(r.program_names),
                          programs_counted=len(set(r.program_of_record.values()) - {""}),
                          program_groups_open=len(r.program_proposals))
        if not view.results_stale:
            view = view.with_(counts=counts_view(r), confidence=confidence_view(s))
    pre = preflight
    if pre is not None:
        view = view.with_(backend=pre.backend_name, release=pre.release, release_stale=pre.release_stale)
    view = view.with_(checks=check_rows(pre, font_ok=ui.get("font_ok", True), secret_ok=ui.get("secret_ok", True),
                                        store_ok=ui.get("store_ok", True), dpapi_ok=ui.get("dpapi_ok", True),
                                        guard_ok=ui.get("guard_ok", False), windows=ui.get("windows", "")))
    return view
