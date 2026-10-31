"""The final feature ledger (M15): every feature from the decisions doc, the build brief, M10 to M14's tables and the old
parity test has a home in the built window, or a reason it was dropped. A missing widget fails."""
import importlib
import tomllib

import pytest
from PySide6.QtWidgets import QWidget

from tests.conftest import ROOT
from tests.support.example_session import example_session
from tests.support.m11 import window_for
from tests.ui.conftest import settle

LEDGER = tomllib.loads((ROOT / "tests" / "ui" / "feature_ledger.toml").read_text(encoding="utf-8"))["feature"]
DECISIONS = (ROOT / "docs" / "context" / "project-docs" / "crosswalk-redesign-decisions.md").read_text(encoding="utf-8")
SOURCES = {"decisions: kept and drawn", "decisions: moved, not drawn yet", "decisions: stages not drawn yet, needs a home",
           "build brief and M10 to M15 tables", "legacy/tests/test_parity.py"}


def kept_items():
    """The decisions doc's "Kept and drawn" list, split on commas outside brackets."""
    line = next(x for x in DECISIONS.splitlines() if x.startswith("Kept and drawn:"))[len("Kept and drawn: "):].rstrip(".")
    items, depth, cur = [], 0, ""
    for ch in line:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return items + [cur.strip()]


def resolve_code(path):
    parts = path.split(".")
    for cut in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:cut]))
        except ImportError:
            continue
        for p in parts[cut:]:
            obj = getattr(obj, p, None)
            if obj is None:
                return None
        return obj
    return None


@pytest.fixture(scope="module")
def built(qapp, tmp_path_factory):
    """Every stage built once over the example session after Process: {stage: set of objectNames}."""
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.stages import STAGES
    from wholecount.ui.frame.window import MainWindow

    s = example_session(tmp_path_factory.mktemp("ledger"))
    w = MainWindow(SessionBridge(s, {"saved_progress": False, "reviewer_asked": True}), clock=lambda: F.NOW,
                   confirm=lambda *a, **k: True)
    w.resize(1440, 900)
    w.show()
    names = {}
    for st in STAGES:
        w.go_to(st.id)
        settle(qapp)
        names[st.id] = {c.objectName() for c in w.stage_widget.findChildren(QWidget) if c.objectName()}
    names["frame"] = {c.objectName() for c in w.findChildren(QWidget) if c.objectName()}
    w.hide()
    return names


def test_rows_are_well_formed():
    for row in LEDGER:
        assert row["source"] in SOURCES, row["name"]
        assert row["status"] in ("built", "dropped"), row["name"]
        if row["status"] == "dropped":
            assert row["widget"] == "dropped" and len(row.get("dropped_by", "")) > 20, row["name"]


def test_every_kept_and_drawn_item_has_a_row():
    rows = {r["name"] for r in LEDGER if r.get("kept_item")}
    assert set(kept_items()) == rows


@pytest.mark.parametrize("row", [r for r in LEDGER if r["status"] == "built"], ids=lambda r: r["name"][:50])
def test_each_built_feature_is_found(built, row):
    w = row["widget"]
    if w.startswith("code:"):
        assert resolve_code(w[5:]) is not None, w
    else:
        assert w in built[row["stage"]], (row["stage"], w)


def test_a_missing_widget_is_caught(built):
    assert "noSuchWidget" not in built["review"]
    assert resolve_code("wholecount.ui.stages.review.queue.NoSuchView") is None
