"""A-23: the old note and Close button hid until the pointer rested on the menu. Both are visible at every width with no
hover and no focus."""
import pytest

from tests.ui.conftest import make_window, themed  # noqa: F401  fixtures
from tools import screen_fixtures as F
from wholecount import copy


def _inside(w, widget):
    tl = widget.mapTo(w, widget.rect().topLeft())
    br = widget.mapTo(w, widget.rect().bottomRight())
    return widget.isVisible() and tl.x() >= 0 and tl.y() >= 0 and br.x() <= w.width() and br.y() <= w.height()


@pytest.mark.claim("CL-OFFLINE-02")
@pytest.mark.claim("CL-OFFLINE-03")
@pytest.mark.parametrize("width", [1280, 1366, 1440, 1920])
def test_close_and_trust_visible_without_hover(make_window, width):
    w = make_window(F.after_run(), width=width, height=800)
    if w.compact:
        assert _inside(w, w.topbar.close_button)
        assert w.topbar.offline.text() == copy.get("top.offline_narrow")
        assert _inside(w, w.topbar.offline)
    else:
        assert _inside(w, w.ledger.close_button)
        assert _inside(w, w.ledger.trust)
        assert w.ledger.trust.text().startswith(copy.get("ledger.foot.trust_offline"))
        assert w.topbar.offline.text() == copy.get("top.offline")
