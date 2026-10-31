"""The user guide (M15 section 1): nine sections in order, the stages in STAGES order, the file equals the generator, the
app and the file share headings, and the dialog opens links nowhere."""
import pytest
from PySide6.QtCore import Qt

from tests.conftest import ROOT
from tests.ui.conftest import settle
from tools import make_docs
from wholecount import copy
from wholecount.copy.guide import build_guide, headings, to_html, to_markdown
from wholecount.ui.frame.stages import STAGES

SECTIONS = ["what", "before", "stages", "results", "files", "data", "words", "trouble", "example"]


def test_nine_sections_in_order_and_the_stages_in_order():
    g = build_guide()
    assert [s.anchor for s in g.sections] == SECTIONS
    stage_heads = [b.text for b in g.sections[2].blocks if b.kind == "h3"]
    assert stage_heads == [f"{s.nn}. {s.plain}" for s in STAGES]


def test_the_file_equals_the_generator():
    assert make_docs.check() == []
    assert (ROOT / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8") == to_markdown(build_guide())


def test_the_app_and_the_file_have_the_same_headings():
    g = build_guide()
    md, html = to_markdown(g), to_html(g)
    for h in headings(g):
        assert h in md and h in html.replace("&#x27;", "'")


def test_negative_control_for_the_check(tmp_path, monkeypatch):
    bad = tmp_path / "USER_GUIDE.md"
    bad.write_text(to_markdown(build_guide()).replace("Goal 1", "Goal One", 1))
    monkeypatch.setattr(make_docs, "GUIDE", bad)
    assert make_docs.check()


def test_the_dialog_opens_no_links_and_closes_on_escape(make_window, qtbot, qapp):
    w = make_window()
    d = w.open_guide()
    settle(qapp)
    assert d.isVisible() and (d.width(), d.height()) == (920, 700)
    assert not d.browser.openLinks() and not d.browser.openExternalLinks()
    assert "http" not in d.browser.toPlainText().lower() and "http" not in to_html(d.guide).lower()
    assert d.contents.count() == 9
    qtbot.keyClick(d, Qt.Key_Escape)
    settle(qapp)
    assert not d.isVisible()


def test_f1_and_the_your_data_link_open_it(make_window, qtbot, qapp):
    w = make_window()
    w.your_data.open_()
    w.your_data.guide_link.click()
    settle(qapp)
    assert w.guide is not None and w.guide.isVisible()
    w.guide.reject()
    w.guide = None
    w.guide_shortcut.activated.emit()
    settle(qapp)
    assert w.guide is not None and w.guide.isVisible()
    assert w.your_data.guide_link.text() == copy.get("guide.open")


@pytest.mark.claim("CL-GUIDE-FILES-01")
def test_the_file_counts_follow_the_writer(tmp_path):
    from tests.support.example_session import decide, example_session
    from tests.support.outputs import write
    from wholecount.copy.guide import file_counts

    default, points, practice = file_counts()
    s = decide(example_session(tmp_path))
    assert len(write(s, tmp_path / "p").files) == practice
    s2 = decide(example_session(tmp_path / "n" if (tmp_path / "n").mkdir() is None else tmp_path, practice=False))
    assert len(write(s2, tmp_path / "d").files) == default
    assert len(write(s2, tmp_path / "m", map_points=True).files) == points
