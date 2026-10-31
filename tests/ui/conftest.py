"""UI test fixtures: the theme applied once, and a window over a fixed FrameView."""
import pytest

from tools import screen_fixtures as F


@pytest.fixture(scope="session", autouse=True)
def themed(qapp):
    from wholecount.ui.theme.apply import apply_theme

    apply_theme(qapp)
    return qapp


def settle(app, n=6):
    for _ in range(n):
        app.processEvents()


class Confirm:
    """Stands in for the confirmation dialog: records what it was asked and answers as told."""

    def __init__(self, answer=True):
        self.answer = answer
        self.asked = []

    def __call__(self, title, lines, yes, no):
        self.asked.append((title, tuple(lines), yes, no))
        return self.answer


@pytest.fixture
def make_window(qtbot, qapp):
    from wholecount.ui.frame.bridge import StaticBridge
    from wholecount.ui.frame.window import MainWindow

    made = []

    def make(view=None, width=1440, height=980, stage="sources", bridge=None, confirm=None):
        b = bridge or StaticBridge(view if view is not None else F.idle())
        w = MainWindow(b, clock=lambda: F.NOW, confirm=confirm or Confirm(True))
        qtbot.addWidget(w)
        w.resize(width, height)
        w.show()
        w.go_to(stage)
        settle(qapp)
        made.append(w)
        return w

    yield make
    for w in made:
        w.closing_confirmed = True
        if w.bridge.runner.running:
            w.bridge.cancel_job()
            w.bridge.runner.wait()
