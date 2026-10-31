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
    ("fast path with blockers and warnings", "M11", "01 fast path card", "stage:sources.process_all"),
    ("example data, drop and browse", "M11", "01 drop zone", "stage:sources.zone"),
    ("corrections file recognition and sensitive columns", "M11", "01 notices", "stage:sources.notices"),
    ("include and exclude tables, Show data", "M11", "01 list", "stage:sources.list"),
    ("header row picker", "M11", "DataPreview", "preview"),
    ("resume notice and saved set-ups", "M11", "01 resume card, SetupsPanel", "stage:sources.setups"),
    ("schema editing", "M11", "02", "stage:schema.add_button"),
    ("five tidy-up rules, origin tags, remove and restore, three groupings", "M11", "03", "stage:prepare.rule_cards"),
    ("per-table matching, column check, defaults, date order, two-digit rule, blocked band", "M11", "04",
     "stage:map.confirm"),
    ("program columns, name groups, preview", "M11", "05", "stage:programs.refresh_btn"),
    ("rename a built-in field", "M11", "dropped by SPEC 4.1", "dropped"),
    ("run settings, pre-run summary, run panel, cancel, log, confidence callout, rows found with both balances", "M12",
     "06", "stage:run.settings_box"),
    ("reviewer name, three tabs, grouped decisions, bulk accept with sample, typed count, reason and second sign-off, "
     "send to row by row, preview, fill from street, matching diagnosis, cross-file note, finish review", "M12",
     "07 step 1", "stage:review.accept_all"),
    ("queue with status filter, facets, search, page size, select page and all matching, bulk approve, set aside, "
     "return to open, keep one per program", "M12", "07 step 2", "class:wholecount.ui.stages.review.queue.QueueView"),
    ("record panel with meaning, original row, unmatched columns on screen, shared identifier, suggestion, approve, "
     "set aside, open the source file", "M12", "07 RecordPanel", "class:wholecount.ui.stages.review.record.RecordPanel"),
    ("compare copies, no longer apply list, signed corrections file", "M12", "07", "stage:review.corrections_result"),
    ("two counts with range, open pairs, automatic joins with split, program bars, locations, person table, "
     "printable page", "M12", "08", "stage:summary.page_button"),
    ("ten files, three formats, column chips, exact coordinates, Map_Points, synced folder callout, low confidence "
     "hold, receipt, set-ups", "M12", "09", "stage:export.download"),
    ("reject, set a field on all selected, privacy offset switch and seed, send unplaced rows to review", "M12",
     "dropped by Q7, P-GEO-7 and P-VAL-2", "dropped"),
]


def _resolve(w, path):
    if path == "dropped":
        return "dropped by SPEC 4.1"
    if path.startswith("stage:"):
        stage, attr = path[6:].split(".", 1)
        w.go_to(stage)
        return getattr(w.stage_widget, attr, None)
    if path.startswith("class:"):
        import importlib

        mod, _, name = path[6:].rpartition(".")
        return getattr(importlib.import_module(mod), name, None)
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
