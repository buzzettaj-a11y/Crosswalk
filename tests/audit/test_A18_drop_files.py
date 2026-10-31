"""A-18: the old screen said "drop files here" and dropping did nothing. Dropping local files on Add your files adds them;
anywhere else a drop is refused and no text field receives a path."""
import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QLineEdit

from tests.support.m11 import empty_session, run_job, window_for, write_csv
from tests.ui.conftest import settle, themed  # noqa: F401  fixture
from wholecount import copy


def mime(urls):
    m = QMimeData()
    m.setUrls(urls)
    return m


def enter(target, m):
    ev = QDragEnterEvent(QPointF(5, 5).toPoint(), Qt.CopyAction, m, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, ev)
    return ev


def drop(target, m):
    ev = QDropEvent(QPointF(5, 5), Qt.CopyAction, m, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, ev)
    return ev


@pytest.fixture
def two_files(tmp_path):
    return [write_csv(tmp_path / f"drop{i}.csv", ["First Name", "Last Name", "Client ID"], [["Ana", "Lee", str(i)]])
            for i in (1, 2)]


@pytest.mark.claim("CL-DROP-WORKS-01")
@pytest.mark.parametrize("on", ["zone", "body"])
def test_dropping_two_local_files_adds_both(qtbot, qapp, tmp_path, two_files, on):
    s = empty_session(tmp_path / "s")
    w = window_for(qtbot, qapp, s)
    body = w.stage_widget
    target = body.zone if on == "zone" else body
    m = mime([QUrl.fromLocalFile(str(p)) for p in two_files])
    ev = enter(target, m)
    assert ev.isAccepted()
    assert body.zone.state == "ok" and body.zone.title.text() == copy.get("src.drop.over", n=2)
    run_job(qtbot, qapp, w, lambda: drop(target, m).isAccepted())
    assert sorted(p.name for p in s.setup.paths()) == ["drop1.csv", "drop2.csv"]


def test_drops_elsewhere_start_nothing_and_insert_no_text(qtbot, qapp, tmp_path, two_files):
    s = empty_session(tmp_path / "s")
    w = window_for(qtbot, qapp, s, stage="schema")
    m = mime([QUrl.fromLocalFile(str(p)) for p in two_files])
    edit = w.stage_widget.findChild(QLineEdit, "newName")
    for target in (edit, w.topbar, w.stage_widget):
        ev = enter(target, m)
        assert not ev.isAccepted()
        drop(target, m)
    settle(qapp)
    assert edit.text() == ""
    assert w.bridge.runner.threads_started == 0 and not s.setup.paths()


@pytest.mark.claim("CL-DROP-UNC-01")
def test_non_local_folders_and_network_addresses_are_refused(qtbot, qapp, tmp_path, two_files):
    s = empty_session(tmp_path / "s")
    w = window_for(qtbot, qapp, s)
    body = w.stage_widget
    remote = QUrl()
    remote.setScheme("ftp")
    remote.setHost("example.org")
    remote.setPath("/a.csv")
    for urls, msg in (([remote], "src.drop.not_local"), ([QUrl.fromLocalFile(str(tmp_path))], "src.drop.not_local"),
                      ([QUrl.fromLocalFile("//server/share/list.csv")], "src.drop.network_address")):
        ev = enter(body, mime(urls))
        assert not ev.isAccepted()
        assert body.zone.state == "bad" and body.zone.message.text() == copy.get(msg)
        drop(body, mime(urls))
    assert w.add_files([type(two_files[0])("\\\\server\\share\\list.csv")]) is False
    assert w.bridge.runner.threads_started == 0 and not s.setup.paths()


def test_the_zone_says_drop_only_because_dropping_works():
    """The copy says Drop, and the test above proves a drop adds the files (CL-DROP-WORKS-01)."""
    assert copy.get("src.drop.title").startswith("Drop")
