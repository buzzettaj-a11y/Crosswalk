"""Download (M12 section 4): the balance band and the files agree, the Low hold, exact coordinates, moved points, the receipt
and the footer, and a download switch that changes no result."""
import pathlib

import pytest
from PySide6.QtWidgets import QCheckBox, QLabel

from tests.support.example_session import decide, example_session
from tests.support.m11 import run_job, window_for
from tests.support.outputs import header, read
from tests.support.write_spy import WriteSpy
from tests.ui.conftest import settle
from wholecount import copy

UI = {"reviewer_asked": True}


def download(qtbot, qapp, w, folder):
    folder.mkdir(parents=True, exist_ok=True)
    run_job(qtbot, qapp, w, lambda: w.stage_widget.start(folder))
    w.refresh()
    settle(qapp)


def door_session(tmp_path):
    from tests.fixtures.outputs.fixture import districts
    from tests.fixtures.session import r_fixture
    from tests.support.files_run import ack, run, write_csv

    rows = [[f"D{i:04d}", f"Given{i}", f"Family{i}", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"]
            for i in range(30)]
    cols = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
    s = run(tmp_path, [write_csv(tmp_path / "in" / "door.csv", cols, rows)], districts=districts(tmp_path),
            backend=r_fixture.reference())
    return ack(s)


@pytest.mark.claim("CL-HOLD-LOW-01")
def test_download_is_held_until_low_is_ticked(qtbot, qapp, tmp_path):
    from tests.support.session import base

    s = base(tmp_path)
    assert s.results.confidence.level == "low"
    w = window_for(qtbot, qapp, s, stage="export", ui=UI)
    b = w.stage_widget.download
    assert b.held and b.caption.text() == "Download is held until the Low confidence is ticked as seen."
    assert w.stage_widget.start(tmp_path / "never") is False and not (tmp_path / "never").exists()
    w.acknowledge_low()
    settle(qapp)
    assert not w.stage_widget.download.held


@pytest.mark.claim("CL-BALANCE-FILES-01")
@pytest.mark.claim("CL-RECEIPT-ONLY-01")
@pytest.mark.claim("CL-RECEIPT-ONLY-02")
def test_the_band_matches_the_files_and_the_receipt_lists_every_write(qtbot, qapp, tmp_path, monkeypatch):
    s = decide(example_session(tmp_path))
    w = window_for(qtbot, qapp, s, stage="export", ui=UI)
    body = w.stage_widget
    assert body.findChild(QLabel, "exportFooter").text() == "Nothing has been written yet."
    bal = s.results.counts
    band = body.findChild(QLabel, "exportBand").text()
    received = s.results.balance.total("received")
    assert band == copy.get("export.band", counted=bal.counted, not_counted_yet=bal.not_counted_yet, aside=bal.set_aside,
                            received=received)
    out = tmp_path / "out"
    with WriteSpy(monkeypatch) as spy:
        download(qtbot, qapp, w, out)
    names = {p.name for p in out.iterdir()}
    receipt = body.receipt
    assert names == {pathlib.Path(f.path).name for f in receipt.files}
    # Every write went into the chosen folder, under a receipt name or its temporary ".name.part" twin.
    written = [pathlib.Path(w[0] if isinstance(w, tuple) else w) for w in spy.writes]
    assert written and all(x.parent == out for x in written)
    assert {x.name.removeprefix(".").removesuffix(".part") for x in written} <= names
    assert body.findChild(QLabel, "receiptNothing").text() == "Nothing else was written."
    assert body.findChild(QLabel, "exportFooter").text() == copy.get("export.footer.after")
    pre = "PRACTICE_" if s.results.practice else ""
    clean = read(out / f"{pre}Final_Clean_Mapped.csv")
    review = read(out / f"{pre}Manual_Review_Needed.csv")
    aside = read(out / f"{pre}Set_Aside_Records.csv")
    clean = [r for r in clean if r.get("Record_Key")]
    assert len(clean) + sum(1 for r in review if r["Counted"] == "No") + len([r for r in aside if r.get("Record_Key")]) \
        == received


@pytest.mark.claim("CL-COORDS-INTERNAL-01")
def test_exact_coordinates_add_the_columns_and_the_note(qtbot, qapp, tmp_path):
    s = door_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="export", ui=UI)
    body = w.stage_widget
    assert body.findChild(QLabel, "coordsNote") is None
    body.findChild(QCheckBox, "exactCoordinates").setChecked(True)
    settle(qapp)
    assert w.stage_widget.findChild(QLabel, "coordsNote").text() == copy.get("export.coords.note")
    assert not w.stage_widget.download.held
    download(qtbot, qapp, w, tmp_path / "out")
    assert {"Latitude", "Longitude"} <= set(header(tmp_path / "out" / "Final_Clean_Mapped.csv"))


@pytest.mark.claim("CL-OFFSET-NOTE-01")
def test_map_points_are_moved_and_shared_by_a_building(qtbot, qapp, tmp_path):
    from tests.fixtures.session import r_fixture
    from wholecount.engine.geo.offset import haversine_ft

    s = door_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="export", ui=UI)
    box = w.stage_widget.findChild(QCheckBox, "writeMapPoints")
    assert box.isEnabled() and not box.isChecked()
    assert copy.get("export.file.map_points") in [x.text() for x in w.stage_widget.findChildren(QLabel)]
    n = len(w.stage_widget.settings().formats) and w.stage_widget.download.button.text()
    box.setChecked(True)
    settle(qapp)
    # A download switch changes no result: nothing is held and the switch stays to turn it off again.
    assert not s.stale and not w.stage_widget.download.held
    again = w.stage_widget.findChild(QCheckBox, "writeMapPoints")
    assert again is not None and again.isChecked()
    assert w.stage_widget.download.button.text() != n
    download(qtbot, qapp, w, tmp_path / "out")
    pts = read(tmp_path / "out" / "Map_Points.csv")
    assert len(pts) == 30 and len({(p["Latitude"], p["Longitude"]) for p in pts}) == 1
    door = r_fixture.GAZETTEER[0]
    assert 149.5 <= haversine_ft(door[4], door[5], float(pts[0]["Latitude"]), float(pts[0]["Longitude"])) <= 250.5


def test_practice_holds_the_map_points_switch_with_its_reason(qtbot, qapp, tmp_path):
    s = decide(example_session(tmp_path))
    w = window_for(qtbot, qapp, s, stage="export", ui=UI)
    box = w.stage_widget.findChild(QCheckBox, "writeMapPoints")
    assert box is not None and not box.isEnabled() and not box.isChecked()
    assert box.accessibleDescription() == copy.get("outputs.practice.no_maps")
    assert w.stage_widget.findChild(QLabel, "practiceNoMaps").text() == copy.get("outputs.practice.no_maps")
