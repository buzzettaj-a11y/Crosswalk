"""Stages 01 to 05 inside the frame (M11): widths with maximal content, 36px targets, holds during a run, data lines on the
real bodies, help entries and the feature ledger rows."""
import pytest
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit, QWidget

from tests.fixtures.session import r_fixture
from tests.support.m11 import window_for, write_csv
from tests.ui.conftest import settle
from wholecount import copy
from wholecount.engine.geo.backend import NoBackend
from wholecount.ui.widgets.dataline import PARTS, part_text

STAGES = ("sources", "schema", "prepare", "map", "programs")
WIDTHS = (1280, 1366, 1440, 1920)


@pytest.fixture(scope="module")
def big_files(tmp_path_factory):
    d = tmp_path_factory.mktemp("big")
    header = ["First Name", "Last Name", "Client ID", "DOB", "Address", "Zip", "Program"] + [f"Extra column {i:02d}" for i in range(53)]
    paths = []
    for n in range(9):
        name = f"{'partner_export_with_a_long_name_' + str(n):<36}".replace(" ", "x")[:36] + ".csv"
        rows = [[f"Ana{chr(65 + r)}", f"Lee{chr(66 + r)}", f"{n}{r:03d}", "01/02/1980", f"{r + 1} Main St", "11201",
                 ["Youth Services", "Youth Svcs", "Housing"][r % 3]] + [f"v{r}"] * 53 for r in range(12)]
        paths.append(write_csv(d / name, header, rows))
    return paths


def big_session(tmp_path, paths):
    return r_fixture.session(tmp_path, backend=NoBackend(), paths=paths)


def controls(w):
    out = []
    for cls in (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox):
        out += [c for c in w.findChildren(cls) if c.isVisible()
                and not (isinstance(c, QLineEdit) and isinstance(c.parentWidget(), (QAbstractSpinBox, QComboBox)))]
    return out


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("stage", STAGES)
def test_stage_fits_every_width_with_maximal_content(qtbot, qapp, tmp_path, big_files, stage, width):
    s = big_session(tmp_path, big_files)
    w = window_for(qtbot, qapp, s, stage=stage, width=width)
    assert w.stage_area.horizontalScrollBar().maximum() == 0
    for c in w.findChildren(QWidget):
        if c.isVisible() and not c.isWindow() and c.objectName() != "liveRegion":
            assert c.mapTo(w, c.rect().topRight()).x() <= width, (c.metaObject().className(), c.objectName())
    for c in controls(w):
        assert c.height() >= 36, (c.metaObject().className(), c.objectName(), c.height())


@pytest.mark.parametrize("stage", STAGES)
def test_every_data_control_is_held_during_a_run(qtbot, qapp, tmp_path, big_files, stage):
    s = big_session(tmp_path, big_files)
    w = window_for(qtbot, qapp, s, stage=stage)
    w.run_hold.hold()
    held = set(map(id, w.run_hold.registered()))
    body = w.stage_widget
    data = [c for c in body.findChildren(QWidget) if isinstance(c, (QComboBox, QLineEdit, QAbstractSpinBox))
            and c.isVisible() and not isinstance(c.parentWidget(), (QAbstractSpinBox, QComboBox))]
    assert data and all(id(c) in held for c in data), [c.objectName() for c in data if id(c) not in held]
    live = [c for c in body.findChildren(QAbstractButton) if c.objectName().startswith(("continue", "show_", "group_",
                                                                                         "mapShowData"))]
    assert all(id(c) not in held for c in live)
    w.run_hold.release()


@pytest.mark.parametrize("stage", STAGES)
def test_each_stage_shows_its_data_line(qtbot, qapp, tmp_path, big_files, stage):
    s = big_session(tmp_path, big_files)
    w = window_for(qtbot, qapp, s, stage=stage)
    line = w.stage_widget.head.dataline
    for part in PARTS:
        assert line.text(part) == part_text(stage, part, False)


@pytest.mark.parametrize("stage", STAGES)
def test_help_entries_exist(stage):
    from wholecount.ui.widgets.help import HelpButton

    for k in ("title", "purpose", "how"):
        assert copy.get(f"help.stage.{stage}.{k}")
    assert HelpButton(f"stage.{stage}").accessibleName() == f"Help: {copy.get(f'help.stage.{stage}.title')}"
