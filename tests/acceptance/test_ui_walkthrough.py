"""The nine stages through their own widgets (M15): the real window, offscreen, pressing the buttons a person presses. File
dialogs are stubbed to fixed folders and the reviewer prompt is answered with the fixed name. It ends with a receipt whose
data files equal the session route's, which proves the stage bodies, the bridge and the engine agree."""
import pathlib

from PySide6.QtWidgets import QFileDialog, QPushButton, QRadioButton, QWidget

from tests.acceptance import drive
from tests.support.m11 import window_for
from tests.ui.conftest import Confirm, settle
from wholecount.session.pages import cause_views


def press(qapp, w, name, cls=QPushButton):
    b = w.findChild(cls, name)
    assert b is not None and b.isVisible() and b.isEnabled(), name
    b.click()
    settle(qapp)


def held_press(qapp, widget):
    assert not widget.held, widget.objectName()
    widget.button.click()
    settle(qapp)


def wait_job(qtbot, qapp, w, start):
    with qtbot.waitSignal(w.bridge.runner.finished, timeout=60000):
        start()
    settle(qapp)


def test_the_window_drives_all_nine_stages_to_the_same_files(qtbot, qapp, tmp_path, practice_routes, monkeypatch):
    s = drive.new_session()
    w = window_for(qtbot, qapp, s, stage="sources", width=1440, height=900, confirm=Confirm(True))
    plan = drive.PLAN["decisions"]

    # 01 Add your files: Try example data, then the header row the card asks about.
    held_press(qapp, w.stage_widget.zone.example)
    assert sorted(p.name for p in s.setup.paths()) == sorted(drive.NAMES)
    for h in plan["header_rows"]:
        t = next(t for t in w.bridge.survey().tables if t.file_name == h["file"] and t.sheet == h["sheet"])
        press(qapp, w, f"show_{t.letter}_{t.idx}")
        w.preview.radios[h["header_row"]].click()
        settle(qapp)
        w.preview.close_()
        settle(qapp)
    press(qapp, w, "continueSchema")
    assert w.current == "schema"

    # 02 Your columns, 03 Tidy up.
    press(qapp, w, "continuePrepare")
    press(qapp, w, "continueMap")
    assert w.current == "map" and "prepare" in s.confirmed_stages

    # 04 Match your columns: confirm every included table, then go on.
    for _ in w.bridge.survey().works:
        held_press(qapp, w.stage_widget.confirm)
    assert len(s.confirmed_tables) == len(w.bridge.survey().works)
    press(qapp, w, "continuePrograms")
    assert w.current == "programs"

    # 05 Programs: each proposed group is one program, as the plan says.
    for g in plan["program_groups"]:
        press(qapp, w, f"confirm_{g['label']}")
    held_press(qapp, w.stage_widget.cont)
    assert w.current == "run"

    # 06 Process.
    wait_job(qtbot, qapp, w, lambda: held_press(qapp, w.stage_widget.process))
    assert s.results is not None and not s.stale
    press(qapp, w, "goReview")
    assert w.current == "review"

    # 07 Fix problems: the reviewer prompt, then each copy group and same-ID conflict in Compare.
    d = w.stage_widget.dialog
    d.name.setText(drive.REVIEWER)
    d.start.click()
    settle(qapp)
    assert s.reviewer == drive.REVIEWER
    for g in plan["copy_groups"] + plan["same_id_conflicts"]:
        members = {drive._key(s, x) for x in g["rows"]}
        cause = next(v.cause for v in cause_views(s) if set(v.cause.record_keys) & members)
        press(qapp, w, f"compare_{cause.cause_id}")
        panel = w.stage_widget.compare
        while not set(panel.groups[panel.i].members) == members:
            press(qapp, w, "compareNext")
            panel = w.stage_widget.compare
        if "keep" in g:
            w.findChild(QRadioButton, f"keep_{drive._key(s, g['keep'])}").setChecked(True)
            press(qapp, w, "compareSame")
        else:
            press(qapp, w, "compareDifferent")
        press(qapp, w, "compareBack")

    # 08 Results: decide the pairs, then tick Low as seen if the batch is Low.
    w.go_to("summary")
    settle(qapp)
    press(qapp, w, "decidePairs")
    for p in plan["pairs"]:
        a, b = sorted(s.results.person_of_record[drive._key(s, x)] for x in p["rows"])
        pair = next(x for x in s.results.identity.proposals if set(x.pair) == {a, b})
        press(qapp, w, f"pairSame_{pair.pair[0]}" if w.findChild(QPushButton, f"pairSame_{pair.pair[0]}")
              else f"pairSame_{pair.pair[1]}")
    assert s.results.counts.open_pairs == 0 and s.results.counts.open_copy_groups == 0
    if s.results.confidence.level == "low":
        w.acknowledge_low()
        settle(qapp)
    held_press(qapp, w.stage_widget.cont)
    assert w.current == "export"

    # 09 Download, with the folder dialog stubbed to a fixed folder.
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(out)))
    wait_job(qtbot, qapp, w, lambda: held_press(qapp, w.stage_widget.download))
    receipt = w.stage_widget.receipt
    assert receipt is not None

    session_route = practice_routes["fast"][2]
    names = sorted(pathlib.Path(f.path).name for f in receipt.files)
    assert names == sorted(p.name for p in session_route.iterdir())
    for n in names:
        if not n.endswith("_Audit_Log.txt"):
            assert (out / n).read_bytes() == (session_route / n).read_bytes(), n
    assert isinstance(w, QWidget)
