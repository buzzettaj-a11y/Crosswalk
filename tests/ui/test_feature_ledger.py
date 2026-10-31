"""The parity ledger seed (M10): every frame feature from the decisions doc has a home. M11 and M12 add the rest."""
import pytest

from tools import screen_fixtures as F

# (feature, milestone, screen, widget path on MainWindow)
FEATURES = [
    ("undo", "M10", "strip", "strip.undo"),
    ("close", "M10", "ledger footer / top bar", "ledger.close_button"),
    ("close (narrow)", "M10", "top bar", "topbar.close_button"),
    ("start over", "M10", "ledger footer", "ledger.start_button"),
    ("saved progress line", "M10", "top bar", "topbar.saved"),
    ("saved progress switch", "M10", "Your data drawer", "your_data.switch"),
    ("system check", "M10", "ledger footer", "ledger.check_line"),
    ("system check table", "M10", "drawer", "check.table"),
    ("trust sentence", "M10", "ledger footer", "ledger.trust"),
    ("what happens to your data", "M10", "ledger footer", "ledger.your_data"),
    ("settings", "M10", "ledger footer", "ledger.settings"),
    ("reviewer", "M10", "ledger footer", "ledger.reviewer"),
    ("help buttons", "M10", "any stage", "help_button_factory"),
    ("the band", "M10", "narrow", "band"),
    ("details", "M10", "narrow", "details"),
    ("run ticker", "M10", "every stage", "ticker"),
    ("practice tag", "M10", "top bar", "topbar.practice"),
]


def _resolve(w, path):
    if path == "help_button_factory":
        from wholecount.ui.widgets.help import HelpButton
        return HelpButton
    obj = w
    for part in path.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


@pytest.mark.parametrize("feature,milestone,screen,widget", FEATURES)
def test_feature_has_a_widget(make_window, feature, milestone, screen, widget):
    w = make_window(F.after_run())
    assert _resolve(w, widget) is not None, feature


def test_missing_widget_fails(make_window):
    w = make_window(F.after_run())
    assert _resolve(w, "ledger.no_such_widget") is None
