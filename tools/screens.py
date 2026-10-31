"""make screens: render the frame offscreen to build/screens/*.png at 1440x980 and 1280x900 (M10 section 17).

Deterministic: a fixed clock, no animation, no network, fonts only from the bundle. It lives under tools/, so it never ships.

    python -m tools.screens                      render every frame
    python -m tools.screens --demo-run [--practice]   open the real window and run a made-up 30 second Process
"""
import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "screens"
COMMIT = ROOT / "docs" / "milestones" / "screens" / "M10"
COMMIT_M11 = ROOT / "docs" / "milestones" / "screens" / "M11"
COMMIT_M12 = ROOT / "docs" / "milestones" / "screens" / "M12"
COMMIT_M13 = ROOT / "docs" / "milestones" / "screens" / "M13"
M13_TMP = ROOT / "build" / "screens" / "m13-data"
M11_STAGES = ("sources", "schema", "prepare", "map", "programs")
M12_STAGES = ("run", "review", "summary", "export")
SIZES = {1440: (1440, 980), 1280: (1280, 900)}
# The frames the milestone says to commit.
COMMITTED = ("07-review-1440.png", "running-1440.png", "running-1280.png", "low-1440.png", "practice-1440.png",
             "drawer-details-1280.png", "drawer-yourdata-1440.png", "drawer-check-1440.png")


def _app():
    from PySide6.QtWidgets import QApplication

    from wholecount.ui.theme.apply import apply_theme

    app = QApplication.instance() or QApplication([sys.argv[0]])
    apply_theme(app)
    return app


def _settle(app, n=8):
    for _ in range(n):
        app.processEvents()


def window(view, width, stage="sources"):
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import StaticBridge
    from wholecount.ui.frame.window import MainWindow

    w = MainWindow(StaticBridge(view), clock=lambda: F.NOW, confirm=lambda *a: False)
    w.resize(*SIZES[width])
    w.show()
    w.go_to(stage)
    return w


def session_window(populated, width, stage, processed=False):
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = F.example_session(populated)
    if processed:
        from wholecount.session import commands as C
        from wholecount.session.survey import survey

        for g in survey(s).program_map.unconfirmed:
            s.history.execute(C.DecideProgramGroup("confirm", tuple(g.members), g.label))
        from wholecount.session.runner import process

        process(s)
        s.reviewer = "Reviewer"
    ui = {"saved_progress": False, "practice": populated, "example_loaded": populated, "reviewer_asked": processed}
    w = MainWindow(SessionBridge(s, ui, clock=lambda: F.NOW), clock=lambda: F.NOW, confirm=lambda *a: False)
    w.resize(*SIZES[width])
    w.show()
    w.go_to(stage)
    return w


def running_model(upto_place=True):
    from tools import screen_fixtures as F
    from wholecount.session.progress import ProgressMessage, Step
    from wholecount.ui.jobs.model import ProgressModel
    from wholecount.ui.jobs.steps import weights

    m = ProgressModel("process")
    found = {
        Step.READING_FILES: ProgressMessage("progress.found.reading_files", {"read": 5, "unreadable": 0}),
        Step.TIDYING_UP: ProgressMessage("progress.found.demo", {"n": 7412}),
        Step.CHECKING_EVERY_ROW: ProgressMessage("progress.found.demo", {"n": 7412}),
    }
    for s, w in zip(m.steps, weights("process")):
        if upto_place and s.short == "place":
            m.begin(s.step, 7412)
            m.progress(s.step, 4210, 7412, ProgressMessage("progress.placing_in", {"source": F.DEMO_FILE}))
            break
        m.begin(s.step, 7412)
        m.progress(s.step, 7412, 7412, None)
        m.end(s.step, found.get(s.step, ProgressMessage("progress.found.demo", {"n": 7412})), round(30.5 * w, 1))
    return m


def show_running(w):
    from tools import screen_fixtures as F

    w.bridge.fixed = w.bridge.fixed.with_(running=True)
    w.model = running_model()
    w.ticker.start()
    w.run_hold.hold()
    w.refresh()
    w.ticker.show_progress(w.model)
    w.strip.set_run_fractions({sid: w.model.stage_fraction(sid) for sid in w.model.owners()})
    assert F


def m12_running(width):
    """Process mid-run: a made-up job on the real window over the example files, grabbed while it goes."""
    import time

    from tools import screen_fixtures as F

    w = session_window(True, width, "run")
    app = _app()
    w.start_job(F.DemoJob(seconds=30.5))
    end = time.monotonic() + 1.6
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)

    def stop():
        w.bridge.runner.cancel()
        w.bridge.runner.wait()
        _settle(app)
    w.cleanup = stop
    return w


def m12_frames():
    """Stages 06 to 09 before a run, mid-run and after a sample run, plus the extra frames M12 names."""
    from wholecount.ui.frame.stages import BY_ID

    out = []
    for sid in M12_STAGES:
        for width in SIZES:
            base = f"m12-{BY_ID[sid].nn}-{sid}"
            out.append((f"{base}-before-{width}.png", width, lambda sid=sid, width=width: session_window(True, width, sid)))
            if sid == "run":
                out.append((f"{base}-running-{width}.png", width, lambda width=width: m12_running(width)))
            out.append((f"{base}-after-{width}.png", width,
                        lambda sid=sid, width=width: session_window(True, width, sid, processed=True)))

    def step2(width):
        from wholecount.session.pages import QueueFilter

        w = session_window(True, width, "review", processed=True)
        w.stage_widget.set_step(2, QueueFilter())
        _settle(_app())
        q = w.stage_widget.queue
        if q.data.rows:
            q._open_key(q.data.rows[0].record_key)
        return w

    def accept(width):
        from wholecount.session.pages import cause_views

        w = session_window(True, width, "review", processed=True)
        c = next(v.cause for v in cause_views(w.bridge.session) if v.cause.cause_id == "no_identifier")
        w.stage_widget.accept_all(c)
        return w

    def pairs(width):
        w = session_window(True, width, "summary", processed=True)
        w.stage_widget._open_pairs()
        return w

    for width in SIZES:
        out += [(f"m12-07-review-step2-{width}.png", width, lambda width=width: step2(width)),
                (f"m12-07-review-accept-{width}.png", width, lambda width=width: accept(width)),
                (f"m12-08-summary-pairs-{width}.png", width, lambda width=width: pairs(width))]
    return out


def m13_window(width, state, practice=False):
    """A processed example batch with the saved crosswalk off, on or orphaned. Not practice unless asked, so Measure matching
    is open. The crosswalk and calibration files go to build/screens/m13-data, never to the real data folder."""
    import shutil

    from tools import screen_fixtures as F
    from wholecount.session.crosswalk import TurnOnCrosswalk
    from wholecount.session.secret_store import InstallSecret
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    folder = M13_TMP / f"{state}-{width}"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    s = F.example_session(True)
    if not practice:
        from wholecount.engine.geo.backend import NoBackend

        s.backend, s.allow_sample = NoBackend(), False
    s.crosswalk_path = folder / "crosswalk.db"
    s.calibration_dir = folder / "calibration"
    if state in ("on", "orphaned"):
        real = s.secret
        if state == "orphaned":
            s.secret = InstallSecret(b"m13-screens-another-secret-32-by")
        TurnOnCrosswalk("Reviewer").run(s)
        s.secret = real
    from wholecount.session import commands as C
    from wholecount.session.runner import process
    from wholecount.session.survey import survey

    for g in survey(s).program_map.unconfirmed:
        s.history.execute(C.DecideProgramGroup("confirm", tuple(g.members), g.label))
    process(s)
    s.reviewer = "Reviewer"
    b = SessionBridge(s, {"saved_progress": False, "reviewer_asked": True}, clock=lambda: F.NOW)
    b.dpapi = (lambda x: x, lambda x: x)
    w = MainWindow(b, clock=lambda: F.NOW, confirm=lambda *a: False)
    w.resize(*SIZES[width])
    w.show()
    w.go_to("run")
    w.settings.open_()
    w.refresh()
    return w


def m13_matching(width, step):
    from wholecount.engine.progress import NullSink
    from wholecount.ui.jobs.actions import CalibrateJob

    w = m13_window(width, "on")
    mw = w.m13.measure.open_window()
    mw.per_band.setValue(5)
    job = CalibrateJob(w.bridge.session, 5, mw._drawn, *w.bridge.dpapi)
    job.apply(w.bridge.session, job.run(NullSink()))
    if step == "draw":
        mw.go(0)
    elif step == "label":
        mw.labeler.start("Reviewer")
    else:
        for name in ("Reviewer", "Second Reviewer"):
            mw.labeler.start(name)
            for p in mw.cal.pairs:
                mw.labeler.choose("same" if p.kind == "join" or p.score >= 80 else "different")
            mw.labeler.hand_over()
        for pid in list(mw.cal.disagreements()):
            mw.cal.settle(pid, "different")
        mw.go(4)
    w.matching_dialog = mw
    return w


def _scrolled(w):
    """Scrolls the Settings drawer to M13's cards."""
    app = _app()
    _settle(app)
    w.settings.scroll.verticalScrollBar().setValue(w.m13.secret.mapTo(w.settings.inner, w.m13.secret.rect().topLeft()).y()
                                                   - 12)
    _settle(app)
    return w


def m13_frames():
    out = []
    for width in SIZES:
        for state in ("off", "on", "orphaned"):
            out.append((f"m13-settings-{state}-{width}.png", width,
                        lambda width=width, state=state: _scrolled(m13_window(width, state))))
        for step in ("draw", "label", "results"):
            out.append((f"m13-matching-{step}-{width}.png", width, lambda width=width, step=step: m13_matching(width, step)))
    return out


def frames():
    """(file name, width, builder) for every frame M10 renders."""
    from tools import screen_fixtures as F
    from wholecount.ui.frame.stages import STAGES
    from wholecount.ui.frame.view import RESULT_STAGES
    from wholecount.ui.jobs.runner import JobOutcome

    out = []
    for s in STAGES:
        for width in SIZES:
            out.append((f"{s.nn}-{s.id}-{width}.png", width, lambda width=width, sid=s.id: window(F.idle(), width, sid)))

    def running(width):
        w = window(F.after_run(), width, "run")
        show_running(w)
        w.toggle_steps()
        return w

    def after(width):
        w = window(F.after_run(), width, "summary")
        w.model = running_model(upto_place=False)
        w.ticker.start()
        w.ticker.finished(JobOutcome("process", 30.5, 7), True)
        w.toggle_log()
        return w

    def low(width):
        w = window(F.after_run(confidence=F.confidence("low")), width, "export")
        _settle(_app())
        w.ledger.scroll.verticalScrollBar().setValue(w.ledger.confidence.y() - 12)
        return w

    def drawer(width, name, opener):
        w = window(F.after_run(), width, "review")
        opener(w)
        return w

    for width in SIZES:
        out.append((f"running-{width}.png", width, lambda width=width: running(width)))
    out += [
        ("after-medium-log-1440.png", 1440, lambda: after(1440)),
        ("low-1440.png", 1440, lambda: low(1440)),
        ("stale-1440.png", 1440, lambda: window(F.after_run(stale=frozenset(RESULT_STAGES), counts=None, confidence=None),
                                                1440, "summary")),
        ("practice-1440.png", 1440, lambda: window(F.after_run(practice=True, backend="reference_sample"), 1440, "review")),
        ("held-1440.png", 1440, lambda: (lambda w: (show_running(w), w)[1])(window(F.after_run(), 1440, "run"))),
        ("drawer-details-1280.png", 1280, lambda: drawer(1280, "details", lambda w: w.open_details())),
        ("drawer-yourdata-1440.png", 1440, lambda: drawer(1440, "yourdata", lambda w: w.your_data.open_())),
        ("drawer-check-1440.png", 1440, lambda: drawer(1440, "check", lambda w: w.check.open_())),
    ]
    from wholecount.ui.frame.stages import BY_ID

    for sid in M11_STAGES:
        for state in ("fresh", "populated"):
            for width in SIZES:
                out.append((f"m11-{BY_ID[sid].nn}-{sid}-{state}-{width}.png", width,
                            lambda sid=sid, state=state, width=width: session_window(state == "populated", width, sid)))
    return out + m12_frames() + m13_frames()


def render(names=None, out=OUT):
    app = _app()
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, width, build in frames():
        if names and name not in names:
            continue
        w = build()
        _settle(app)
        scroll = w.ledger.scroll.verticalScrollBar().value()
        w.centralWidget().setFocus()
        _settle(app, 2)
        w.ledger.scroll.verticalScrollBar().setValue(scroll)
        _settle(app, 2)
        path = out / name
        w.grab().save(str(path), "PNG")
        if name.startswith("m12-07-review-accept") and w.stage_widget.dialog is not None:
            _paste_dialog(w, w.stage_widget.dialog, path)
        if getattr(w, "matching_dialog", None) is not None:
            _paste_dialog(w, w.matching_dialog, path)
            w.matching_dialog.close()
        written.append(path)
        if getattr(w, "cleanup", None):
            w.cleanup()
        w.closing_confirmed = True
        w.close()
        w.deleteLater()
        _settle(app, 2)
    return written


def _paste_dialog(w, d, path):
    """A dialog is its own window, so grab() of the main window leaves it out. Draw it centered over the frame."""
    from PySide6.QtGui import QPainter, QPixmap

    frame = QPixmap(str(path))
    shot = d.grab()
    p = QPainter(frame)
    p.fillRect(frame.rect(), QColor_dim())
    x, y = (frame.width() - shot.width()) // 2, (frame.height() - shot.height()) // 3
    p.fillRect(x, y, shot.width(), shot.height(), d.palette().window())
    p.drawPixmap(x, y, shot)
    p.end()
    frame.save(str(path), "PNG")


def QColor_dim():  # noqa: N802
    from PySide6.QtGui import QColor

    return QColor(16, 24, 40, 90)


def demo_run(practice=False):
    """The real window with the fixture view and a made-up Process over about 30 seconds. Nothing is read or written."""
    from tools import screen_fixtures as F

    app = _app()
    w = window(F.after_run(practice=practice), 1440, "run")
    w.on_process = lambda: w.start_job(F.DemoJob(seconds=30.5))
    w.start_job(F.DemoJob(seconds=30.5))
    return app.exec()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.screens")
    ap.add_argument("--demo-run", action="store_true")
    ap.add_argument("--practice", action="store_true")
    ap.add_argument("--commit", action="store_true", help="copy the committed frames to docs/milestones/screens/M10")
    args = ap.parse_args(argv)
    if args.demo_run:
        return demo_run(args.practice)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    paths = render()
    print(f"{len(paths)} frames in {OUT.relative_to(ROOT).as_posix()}")
    if args.commit:
        import shutil

        COMMIT.mkdir(parents=True, exist_ok=True)
        for name in COMMITTED:
            shutil.copy(OUT / name, COMMIT / name)
        COMMIT_M11.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("m11-0*.png"):
            shutil.copy(p, COMMIT_M11 / p.name)
        COMMIT_M12.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("m12-0*.png"):
            shutil.copy(p, COMMIT_M12 / p.name)
        COMMIT_M13.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("m13-*.png"):
            shutil.copy(p, COMMIT_M13 / p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
