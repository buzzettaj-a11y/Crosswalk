"""Progress plumbing (SPEC 11.6, H8, H14): the sink, the model, the runner, cancel, failure and one Undo per job."""
import random

import pytest

from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount import copy
from wholecount.session.progress import ProgressMessage, SourceRef, Step, Unit
from wholecount.ui.jobs.model import ProgressModel
from wholecount.ui.jobs.runner import RUN_LOG, error_code
from wholecount.ui.jobs.sink import QtProgressSink
from wholecount.ui.jobs.steps import ACTIONS, STEPS, steps_of, weights


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_step_lists_are_data_on_the_one_enum():
    assert {s.step for s in STEPS.values()} == set(Step)
    assert [s.short for s in steps_of("process")] == ["read", "tidy", "check", "place", "copies", "people", "count_balance"]
    assert set(ACTIONS) == {"add_files", "process", "preview", "look_up", "download", "resume", "corrections", "calibrate",
                            "backup"}
    for a in ACTIONS:
        assert abs(sum(weights(a)) - 1.0) < 1e-9
    assert round(weights("process")[3] * 30.5, 1) == 18.6
    assert STEPS["draw"].owner is None and STEPS["protect"].owner is None
    assert {STEPS[s].owner for s in ("corr_read", "corr_check")} == {"review"}


def test_bar_never_moves_backward_over_shuffled_advances():
    m = ProgressModel("process")
    rng = random.Random(7)
    seen = []
    for s in m.steps:
        m.begin(s.step, 100)
        values = list(range(0, 101, 5))
        rng.shuffle(values)
        for v in values:
            m.progress(s.step, v, rng.choice([80, 100, 120]))
            seen.append((m.overall_fraction(), {o: m.stage_fraction(o) for o in m.owners()}))
        m.end(s.step, ProgressMessage("progress.found.demo", {"n": 1}), 1.0)
    for (a, sa), (b, sb) in zip(seen, seen[1:]):
        assert b >= a
        assert all(sb[k] >= sa[k] for k in sa)
    assert m.overall_fraction() == 1.0


def test_count_and_total_never_go_down_and_empty_steps_fill_on_end():
    m = ProgressModel("add_files")
    m.begin(Step.READING_FILES, 10)
    m.progress(Step.READING_FILES, 6, 10)
    m.progress(Step.READING_FILES, 3, 4)
    st = m.states[0]
    assert st.done == 6 and st.total == 10
    m.begin(Step.FINDING_TABLES, 0)
    assert m.states[1].fraction == 0.0
    m.end(Step.FINDING_TABLES, ProgressMessage("progress.found.demo", {"n": 0}), 0.0)
    assert m.states[1].fraction == 1.0


def _sink(clock):
    posts = []
    return QtProgressSink(posts.append, clock=clock), posts


def test_a_thousand_advances_in_50ms_make_at_most_two_posts():
    clock = Clock()
    sink, posts = _sink(clock)
    sink.begin(Step.CHECKING_EVERY_ROW, 100000, Unit.ROWS)
    start = len(posts)
    for i in range(1000):
        clock.t = i * 0.00005
        sink.advance(1, ProgressMessage("progress.demo", {"n": i}))
    assert len(posts) - start <= 2


def test_calls_20ms_apart_post_about_every_100ms_with_heartbeats_in_quiet():
    clock = Clock()
    sink, posts = _sink(clock)
    sink.begin(Step.CHECKING_EVERY_ROW, 100000, Unit.ROWS)
    times = []
    orig = sink._post
    sink._post = lambda s: (times.append(clock.t), orig(s))
    for i in range(1, 101):
        clock.t = i * 0.02
        sink.advance(1, ProgressMessage("progress.demo", {"n": i}))
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert gaps and all(0.099 <= g <= 0.121 for g in gaps)
    # a quiet step: no advance for a second, the runner's 250 ms timer re-posts
    last = clock.t
    before = len(times)
    for k in range(1, 5):
        clock.t = last + 0.25 * k
        sink.heartbeat()
    assert len(times) - before == 4
    assert max(b - a for a, b in zip(times, times[1:])) <= 0.25 + 1e-9


@pytest.mark.parametrize("params", [{"who": "Jane Doe"}, ("x",), {"n": True}, {"n": 1.5}])
def test_progress_message_refuses_anything_but_int_sources_and_steps(params):
    with pytest.raises(TypeError):
        ProgressMessage("x", params)


SECRET_VALUES = ("Jane Doe", "209 Joralemon St")


def _all_text(window):
    from PySide6.QtWidgets import QLabel

    return " ".join(w.text() + " " + w.toolTip() for w in window.findChildren(QLabel))


@pytest.mark.claim("CL-FAILED-01")
def test_a_failing_job_shows_a_code_and_never_its_message(make_window, qtbot, qapp):
    from wholecount.ui.frame import a11y

    w = make_window(F.after_run(), stage="run")
    job = F.DemoJob(seconds=0.05, sleep=lambda s: None, raise_in=1, exc=ValueError("Jane Doe, 209 Joralemon St"))
    n_log = len(RUN_LOG)
    with qtbot.waitSignal(w.bridge.runner.failed, timeout=10000):
        assert w.start_job(job)
    settle(qapp)
    text = _all_text(w)
    assert "Something went wrong in Tidying up. Nothing was changed." in text
    assert "Error code E-" in text
    for v in SECRET_VALUES:
        assert v not in text
        assert v not in repr(RUN_LOG[n_log:])
        assert all(v not in a for a in a11y.ANNOUNCED)
    code, type_name, frames = RUN_LOG[-1]
    assert type_name == "ValueError" and code.startswith("E-") and len(code) == 8
    assert job.applied == 0
    assert not w.run_hold.active


def test_error_code_comes_from_type_and_place_not_message():
    def boom(msg):
        raise ValueError(msg)
    codes = set()
    for msg in ("Jane Doe", "someone else"):
        try:
            boom(msg)
        except ValueError as e:
            codes.add(error_code(e))
    assert len(codes) == 1


@pytest.mark.claim("CL-CANCEL-01")
def test_cancel_leaves_the_session_unchanged(tmp_path, qtbot, qapp):
    from tests.support.session import base, snapshot
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = base(tmp_path)
    before = snapshot(s)
    stack = list(s.history.stack)
    log = list(s.audit_log)
    bridge = SessionBridge(s)
    w = MainWindow(bridge, clock=lambda: F.NOW, confirm=lambda *a: True)
    qtbot.addWidget(w)
    w.show()
    gate = {"go": False}

    def sleep(_):
        import time
        time.sleep(0.002)
    job = F.DemoJob(seconds=0.5, sleep=sleep)
    with qtbot.waitSignal(bridge.runner.cancelled, timeout=10000):
        w.start_job(job)
        qtbot.waitUntil(lambda: w.model is not None and w.model.current >= 1, timeout=10000)
        w.ticker.cancel_button.click()
    settle(qapp)
    assert snapshot(s) == before and s.history.stack == stack and s.audit_log == log
    assert job.applied == 0
    assert w.ticker.left.text() == copy.get("ticker.cancelled")
    assert not w.run_hold.active
    w.closing_confirmed = True


def test_one_undo_takes_back_a_finished_job(tmp_path, qtbot, qapp):
    from tests.support.session import base
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = base(tmp_path)
    bridge = SessionBridge(s)
    w = MainWindow(bridge, clock=lambda: F.NOW, confirm=lambda *a: True)
    qtbot.addWidget(w)
    job = F.DemoJob(seconds=0.01, sleep=lambda x: None)
    depth = len(s.history.stack)
    with qtbot.waitSignal(bridge.runner.finished, timeout=10000):
        w.start_job(job)
    settle(qapp)
    assert job.applied == 1 and len(s.history.stack) == depth + 1
    assert w.strip.undo.full_label == copy.get("action.process")
    bridge.undo()
    assert job.undone == 1 and len(s.history.stack) == depth
    assert bridge.ui["run_seconds"] is not None
    w.closing_confirmed = True


def test_only_one_thread_and_start_refuses_while_running(make_window, qtbot, qapp):
    import threading

    w = make_window(F.after_run())
    release = threading.Event()
    job = F.DemoJob(seconds=0.2, sleep=lambda s: release.wait(5))
    r = w.bridge.runner
    assert w.start_job(job)
    assert not w.start_job(F.DemoJob(seconds=0.01, sleep=lambda s: None))
    assert r.threads_started == 1
    release.set()
    with qtbot.waitSignal(r.finished, timeout=10000):
        pass
    settle(qapp)
    assert not r.running


def test_announce_once_per_step_not_per_count(make_window, qtbot, qapp):
    from wholecount.ui.frame import a11y

    w = make_window(F.after_run())
    a11y.ANNOUNCED.clear()
    job = F.DemoJob(seconds=0.01, sleep=lambda s: None)
    with qtbot.waitSignal(w.bridge.runner.finished, timeout=10000):
        w.start_job(job)
    settle(qapp)
    steps = [copy.get(s.name_id) for s in steps_of("process")]
    assert a11y.ANNOUNCED[:7] == steps
    assert len(a11y.ANNOUNCED) == 8


def test_messages_with_a_source_draw_the_mark_and_file_name(make_window):
    from wholecount.ui.widgets.source_mark import SourceMark

    w = make_window(F.after_run())
    m = ProgressModel("process")
    for s in m.steps[:4]:
        m.begin(s.step, 7412)
    m.progress(Step.PLACING_ADDRESSES, 4210, 7412, ProgressMessage("progress.placing_in", {"source": SourceRef("A", "clinic.csv")}))
    w.ticker.start()
    w.ticker.show_progress(m)
    assert w.ticker.left.text() == "Step 4 of 7 · Placing addresses · 4,210 of 7,412"
    assert w.ticker.full_message == "Looking up addresses, clinic.csv"
    assert w.ticker.mark_box.findChild(SourceMark).letter == "A"


@pytest.mark.claim("CL-TICKER-DISK-01")
def test_finished_ticker_text_and_no_disk_writes(make_window, qtbot, qapp, monkeypatch):
    from tests.support.write_spy import WriteSpy

    w = make_window(F.after_run(saved_progress=False))
    with WriteSpy(monkeypatch) as spy:
        with qtbot.waitSignal(w.bridge.runner.finished, timeout=10000):
            w.start_job(F.DemoJob(seconds=0.01, sleep=lambda s: None))
        settle(qapp)
    assert spy.writes == []
    assert w.ticker.second.text() == "7 steps, nothing written to disk"
    assert w.ticker.left.text().startswith("Last run finished in ")


def test_ticker_saved_suffix_and_other_actions(make_window):
    from wholecount.ui.jobs.runner import JobOutcome

    w = make_window(F.after_run())
    w.ticker.finished(JobOutcome("process", 30.5, 7), True)
    assert w.ticker.left.text() == "Last run finished in 30.5 s"
    assert w.ticker.second.text() == "7 steps, nothing written to disk except your saved decisions, encrypted"
    w.ticker.finished(JobOutcome("preview", 2.0, 3), False)
    assert w.ticker.left.text() == "Preview finished in 2.0 s" and w.ticker.second.text() == "3 steps"


def test_dropdown_overlays_without_moving_the_layout(make_window, qtbot, qapp):
    w = make_window(F.after_run(), stage="review")
    w.model = ProgressModel("process")
    w.ticker.start()
    settle(qapp)
    before = w.stage_area.geometry()
    w.toggle_steps()
    settle(qapp)
    assert w.dropdown.isVisible() and w.dropdown.width() <= 560
    assert w.stage_area.geometry() == before
    from PySide6.QtCore import Qt
    qtbot.keyClick(w.stage_area, Qt.Key_Escape)
    settle(qapp)
    assert not w.dropdown.isVisible()
