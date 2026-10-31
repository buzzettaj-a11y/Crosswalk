"""A-21: two old screens hard-coded "Stage 0N of 07". One function builds every stage header, empty states included."""
import re

import pytest

from tests.conftest import ROOT
from tests.ui.conftest import themed  # noqa: F401  fixture
from wholecount import copy
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.frame.stages import STAGES


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("stage", STAGES, ids=lambda s: s.id)
def test_kicker_number_and_name(qtbot, stage, empty):
    h = StageHead(stage.id, empty=empty)
    qtbot.addWidget(h)
    assert h.kicker.text() == f"STAGE {stage.number:02d} OF 09 · {stage.technical}"
    assert h.title.text() == stage.plain


def test_no_stage_count_or_name_literal_outside_the_registry():
    plains = [copy.get(f"stage.{s.id}.name") for s in STAGES]
    for p in (ROOT / "wholecount").rglob("*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if rel == "wholecount/ui/frame/stages.py":
            continue
        src = p.read_text(encoding="utf-8")
        assert not re.search(r"\b[Oo][Ff] 0?[0-9]\b", src), rel
        if rel.startswith("wholecount/ui/"):
            for name in plains:
                if name in ("Programs", "Process", "Results", "Download"):
                    continue
                assert f'"{name}"' not in src and f"'{name}'" not in src, (rel, name)


def test_count_comes_from_the_registry(monkeypatch):
    from wholecount.ui.frame import stages

    monkeypatch.setattr(stages, "STAGES", stages.STAGES[:7])
    assert stages.kicker("review").startswith("STAGE 07 OF 07")
