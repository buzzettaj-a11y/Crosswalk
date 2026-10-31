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
    return out


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
        written.append(path)
        w.closing_confirmed = True
        w.close()
        w.deleteLater()
        _settle(app, 2)
    return written


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
