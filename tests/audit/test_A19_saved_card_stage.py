"""A-19: the old saved-progress card named the wrong stage, and the last two read "in progress". The card takes the name
from STAGES by the stage ID the saved entry holds."""
import pytest

from tests.ui.conftest import themed  # noqa: F401  fixture

from wholecount.ui.frame.stages import IDS, STAGES
from wholecount.ui.widgets.saved_progress_card import SavedProgressCard, card_lines


@pytest.mark.parametrize("stage", IDS)
def test_card_names_the_stored_stage(qtbot, stage):
    plain = next(s.plain for s in STAGES if s.id == stage)
    entry = {"when": "2 min ago", "stage": stage, "files": 5, "decisions": 12}
    lines = card_lines(entry)
    assert lines[1] == f"stopped at {plain}"
    card = SavedProgressCard(entry)
    qtbot.addWidget(card)
    assert plain in card.text() and "in progress" not in card.text()
    assert "5 files" in card.text() and "12 decisions" in card.text()


def test_first_and_last_are_not_shifted():
    assert card_lines({"when": "now", "stage": "sources"})[1] == "stopped at Add your files"
    assert card_lines({"when": "now", "stage": "export"})[1] == "stopped at Download"
    assert card_lines({"when": "now", "stage": "programs"})[1] == "stopped at Programs"


def test_saved_progress_stores_the_stage_id(tmp_path):
    from tests.support.session import base
    from wholecount.session.store import snapshot

    s = base(tmp_path)
    assert snapshot(s)["stage"] == "sources"
    s.stage = "review"
    assert snapshot(s)["stage"] == "review"
