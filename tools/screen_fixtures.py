"""Deterministic FrameViews from the board numbers, for make screens and the frame tests. Made-up counts, no client data."""
import datetime as dt

from wholecount.session.frame import Locations
from wholecount.session.progress import ProgressMessage, SourceRef, Unit
from wholecount.ui.frame.view import CheckRow, ConfidenceView, CountsView, FrameView, PreviewView

NOW = dt.datetime(2026, 10, 31, 14, 30, tzinfo=dt.timezone.utc)
THRESHOLDS = {"high_counted_pct": 95, "high_placed_pct": 95, "high_open_pairs": 0, "low_pct": 80}
LOCATIONS = Locations(high=5802, low=198, no_fixed_address=31, outside_nyc=22, address_problem=19, not_found=12)


def checks(geosupport=True, stale_release=False):
    geo = (CheckRow("geosupport", "warn" if stale_release else "ok",
                    ("check.detail.geosupport_old" if stale_release else "check.detail.geosupport", {"release": "24B"}))
           if geosupport else CheckRow("geosupport", "missing", ("check.detail.geosupport_none", {})))
    return (geo, CheckRow("reference", "missing", ("check.detail.reference_none", {})),
            CheckRow("districts", "ok", ("check.detail.districts", {"n": 3})),
            CheckRow("secret", "ok", ("check.detail.secret_ok", {})), CheckRow("store", "ok", ("check.detail.store_ok", {})),
            CheckRow("dpapi", "ok", ("check.detail.dpapi_ok", {})), CheckRow("font", "ok", ("check.detail.font_ok", {})),
            CheckRow("guard", "ok", ("check.detail.guard_ok", {})),
            CheckRow("windows", "ok", ("check.detail.windows", {"version": "Windows 11 23H2"})))


def counts(final=False, balance_ok=True, not_counted_yet=1232, open_pairs=14, open_groups=0):
    counted = 7412 - not_counted_yet - 96
    loc = LOCATIONS if counted == 6084 else Locations(high=counted - 282, low=198, address_problem=84)
    g1 = (5940, 5940 if final else 5954)
    return CountsView(received=7412, counted=counted, not_counted_yet=not_counted_yet, set_aside=96, goal1=g1,
                      goal2=(7106, 7106 if final else 7121), open_pairs=open_pairs, open_copy_groups=open_groups,
                      is_final=final, locations=loc, balance_ok=balance_ok,
                      lines=(("ledger.standing.sum", {"counted": counted, "not_counted_yet": not_counted_yet,
                                                      "set_aside": 96, "received": 7412}),
                             ("ledger.loc.sum", {"high": loc.high, "low": loc.low, "not_mapped": loc.not_mapped,
                                                 "counted": counted})))


def confidence(level="medium", acknowledged=False, placed=True, calibration=None):
    measures = (("counted", 6084, 7412), ("open_pairs", 14, None),
                ("placed", 5802, 6012) if placed else ("placed", None, None))
    parts = {"medium": (("pairs_open", {"count": 14}),),
             "low": (("counted_short", {"counted": 6084, "received": 7412}), ("pairs_open", {"count": 14})),
             "high": ()}[level]
    if level != "high" and not placed:
        parts = parts + (("placed_unavailable_no_geocoder", {}),)
    return ConfidenceView(level, parts, measures, dict(THRESHOLDS), calibration, acknowledged)


def idle(**kw):
    base = dict(files=0, tables=0, saved_progress=True, saved_at=None, now=NOW, backend="geosupport", release="24B",
                checks=checks(), reviewer=None)
    base.update(kw)
    return FrameView(**base)


def after_run(level="medium", **kw):
    base = dict(files=5, tables=6, rows_in=7412, steps_proposed=4, steps_kept=4, steps_continued=True, map_tables=6,
                map_confirmed=6, map_required=(5, 5), program_files=4, program_names=11, programs_counted=7,
                program_groups_confirmed=3, has_run=True, run_seconds=30.5, rows_open=1232, files_ready=9,
                counts=counts(), confidence=confidence(level), undo_label=("commands.set_aside_rows", {"count": 96}),
                reviewer="J. Rivera", reviewer_asked=True, saved_at=NOW - dt.timedelta(minutes=2),
                preview=PreviewView(5931, 7090, "14:12", stale=False))
    base.update(kw)
    return idle(**base)


def maximal():
    """Five-digit counts and a long caption set, for the layout tests."""
    return after_run(files=12345, tables=23456, rows_in=99999, steps_proposed=12345, steps_noop=1234, map_tables=23456,
                     map_confirmed=12345, map_wrong=4321, program_groups_open=12345, rows_open=99999)


# A made-up job for --demo-run and the tests: the seven Process steps over about 30 seconds. Nothing is read or written.
DEMO_FILE = SourceRef("A", "clinic_export_with_a_long_name_2026.csv")


class DemoJob:
    action_id = "process"

    def __init__(self, seconds=30.5, sleep=None, raise_in=None, exc=None):
        from wholecount.ui.jobs.steps import steps_of, weights

        self.steps = steps_of("process")
        self.durations = tuple(seconds * w for w in weights("process"))
        self.sleep = sleep
        self.raise_in = raise_in
        self.exc = exc
        self.applied = 0
        self.undone = 0

    def run(self, sink):
        import time

        sleep = self.sleep or time.sleep
        for i, (s, d) in enumerate(zip(self.steps, self.durations)):
            total = 7412
            sink.begin(s.step, total, s.unit if isinstance(s.unit, Unit) else Unit.ROWS)
            chunks = 20
            for c in range(chunks):
                if sink.cancelled():
                    return None
                if self.raise_in == i and c == chunks // 2:
                    raise self.exc or ValueError("job failed")
                sleep(d / chunks)
                msg = (ProgressMessage("progress.placing_in", {"source": DEMO_FILE}) if s.short == "place"
                       else ProgressMessage("progress.demo", {"n": total}))
                sink.advance(total // chunks, msg)
            sink.end(ProgressMessage("progress.found.demo", {"n": total}))
        return {"ok": 1}

    def apply(self, session, result):
        self.applied += 1
        return "token"

    def undo(self, session, token):
        self.undone += 1
