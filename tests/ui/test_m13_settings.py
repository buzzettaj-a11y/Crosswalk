"""M13's Settings cards and the Measure matching window, with the claim tests for their sentences."""
import json
import re

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QSpinBox

from tests.support import calibration as K
from tests.support import crosswalk as X
from tests.support.fake_dpapi import FakeDpapi
from tests.support.m11 import run_job, window_for
from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from tests.ui.conftest import Confirm, settle
from wholecount import copy
from wholecount.session.secret_store import FileSecretStore, InstallSecret
from wholecount.session.store import Store

UI = {"reviewer_asked": True}
PASS = "correct horse battery staple"


def texts(w):
    return [x.text() for x in w.findChildren(QLabel)]


def visible_texts(widget):
    return [x.text() for x in widget.findChildren(QLabel) if x.isVisibleTo(widget)]


@pytest.fixture
def xwin(qtbot, qapp, tmp_path):
    """A window over the crosswalk fixture, with the crosswalk path, a key store and prefs set as the app does."""
    def make(confirm=None, xw=None, **kw):
        s = X.session(tmp_path / "b1", xw or tmp_path / "data" / "crosswalk.db", ["batch1_a.csv", "batch1_b.csv"], **kw)
        X.run(s)
        w = window_for(qtbot, qapp, s, stage="run", ui=UI, confirm=confirm)
        w.bridge.secret_store = FileSecretStore(tmp_path / "key")
        w.bridge.secret_store.save(TEST_SECRET)
        w.bridge.prefs_store = Store(tmp_path / "data", protect=lambda b: b, unprotect=lambda b: b)
        w.settings.open_()
        w.refresh()
        settle(qapp)
        return w, s
    return make


def test_the_footer_link_opens_the_drawer_with_four_cards(xwin, qapp):
    w, s = xwin()
    w.settings.close_()
    w.ledger.open_settings.emit()
    settle(qapp)
    assert w.settings.isVisible()
    names = [c.objectName() for c in w.m13.cards]
    assert names == ["secretCard", "crosswalkCard", "linesCard", "measureCard"]
    assert all(w.settings.findChild(type(c), c.objectName()) is c for c in w.m13.cards)


@pytest.mark.claim("CL-XW-CONTENTS-01")
@pytest.mark.claim("CL-XW-NOUNDO-01")
@pytest.mark.claim("CL-XW-FORGET-01")
def test_turn_on_and_forget_the_crosswalk(xwin, qapp, tmp_path):
    from tests.support.outputs import write
    ask = Confirm(True)
    w, s = xwin(confirm=ask)
    card = w.m13.crosswalk
    assert card.state_tag.text() == "Off" and card.on_button.isVisible() and not card.forget_button.isVisible()
    stack = len(s.history.stack)
    assert card.turn_on()
    title, lines, yes, _ = ask.asked[-1]
    assert copy.get("settings.xw.not_undoable") in lines and copy.get("settings.xw.body") in lines
    assert len(s.history.stack) == stack                    # not on the undo stack
    assert s.crosswalk_path.exists()
    settle(qapp)
    assert card.since.isVisible() and card.since.text().startswith("On since ")
    # What it says it holds is what the file holds: no names, addresses, IDs or dates.
    X.run(s)
    X.decide_truth(s)
    from tests.support.files_run import ack
    ack(s)
    write(s, tmp_path / "out")
    raw = s.crosswalk_path.read_bytes()
    for v in ("Rodriguez", "Grand Concourse", "1985-03-14", "A1", "10451"):
        assert v.encode() not in raw
    w.refresh()
    settle(qapp)
    assert card.counts.text() == copy.get("settings.xw.counts", people=10, pairs=4, groups=0)
    w.ask_text = lambda title, prompt: (ask.asked.append((title, (prompt,), "", "")), "forgot")[1]
    assert not card.forget() and s.crosswalk_path.exists()
    assert ask.asked[-1][1] == (copy.get("settings.xw.forget_prompt"),)
    w.ask_text = lambda title, prompt: "forget"
    assert card.forget() and not s.crosswalk_path.exists()
    assert "identity" in s.stale


@pytest.mark.claim("CL-XW-ORPHANED-01")
@pytest.mark.claim("CL-XW-ORPHANED-02")
def test_an_orphaned_crosswalk_says_so_and_is_not_used(xwin, qapp, tmp_path):
    from wholecount.ui.stages.run.body import pre_run_lines
    w, s = xwin()
    X.turn_on(s)
    s.secret = InstallSecret(OTHER_SECRET)
    w.refresh()
    settle(qapp)
    assert w.m13.crosswalk.orphaned.isVisible()
    keys = [k for k, _ in pre_run_lines(s, w.bridge.export_settings())]
    assert keys[-1] == "run.pre.crosswalk_orphaned"
    X.run(s)
    assert s.results.crosswalk is None


@pytest.mark.claim("CL-PASSPHRASE-01")
@pytest.mark.claim("CL-SECRET-ORPHAN-01")
def test_back_up_the_secret(xwin, qtbot, qapp, tmp_path):
    w, s = xwin()
    card = w.m13.secret
    assert card.findChild(QLabel, "secretBody").text() == copy.get("settings.secret.body")
    d = card.backup()
    assert d.first.echoMode() == QLineEdit.Password and d.again.echoMode() == QLineEdit.Password
    assert d.findChild(QLabel, "passBody").text() == copy.get("settings.secret.pass_body", n=12)
    d.first.setText("short")
    d.again.setText("short")
    assert d.save(tmp_path / "s.wcb") is False and d.refusal.text() == "The passphrase needs at least 12 characters."
    d.again.setText("shorter")
    d.save(tmp_path / "s.wcb")
    assert d.refusal.text() == "The two passphrases don't match."
    d.first.setText(PASS)
    d.again.setText(PASS)
    run_job(qtbot, qapp, w, lambda: d.save(tmp_path / "s.wcb"))
    assert (tmp_path / "s.wcb").stat().st_size == 84
    assert card.message.text() == "The backup was saved. It is 84 bytes."
    assert d.first.text() == "" and PASS not in repr(s.audit_log)
    # Losing the secret orphans the crosswalk and saved progress; restoring the backup brings them back.
    from wholecount.session import crosswalk
    X.turn_on(s)
    s.secret = InstallSecret(OTHER_SECRET)
    assert crosswalk.state(s) == "orphaned"
    r = card.restore(tmp_path / "s.wcb")
    r.passphrase.setText(PASS)
    r.word.setText("replace")
    assert r.restore() == "restored"
    assert crosswalk.state(s) == "on"


@pytest.mark.claim("CL-RESTORE-SAME-01")
@pytest.mark.claim("CL-RESTORE-REPLACE-01")
def test_restore_the_secret(xwin, qapp, tmp_path):
    w, s = xwin()
    card = w.m13.secret
    path = tmp_path / "b.wcb"
    path.write_bytes(s.secret.backup(PASS))
    r = card.restore(path)
    r.passphrase.setText("wrong passphrase here")
    assert r.restore() == "refused" and r.message.text() == "The passphrase is wrong or the file is damaged."
    r.passphrase.setText(PASS)
    assert r.restore() == "same" and r.message.text() == "This is the same secret. Nothing changed."
    other = tmp_path / "o.wcb"
    other.write_bytes(InstallSecret(OTHER_SECRET).backup(PASS))
    r = card.restore(other)
    r.passphrase.setText(PASS)
    assert r.restore() == "needs_word" and r.warn.isVisibleTo(r)
    assert r.warn.text() == copy.get("settings.secret.replace_warn")
    assert w.bridge.secret_store.load() == TEST_SECRET          # nothing replaced without the word
    r.passphrase.setText(PASS)
    r.word.setText("replace")
    assert r.restore() == "restored" and w.bridge.secret_store.load() == OTHER_SECRET
    assert "sources" in s.stale


def test_matching_lines_save_to_prefs_and_mark_identity_stale(xwin, qapp, tmp_path):
    w, s = xwin()
    card = w.m13.lines
    assert card.current["possible"].text() == "Now 62" and card.boxes["possible"].value() == 62
    card.boxes["possible"].setValue(70)
    card.boxes["likely"].setValue(95)
    assert card.save()
    assert s.thresholds == (70, 95) and "identity" in s.stale
    prefs = json.loads((tmp_path / "data" / "prefs.json").read_text())
    assert prefs["thresholds"]["possible_min"] == 70
    card.boxes["possible"].setValue(96)
    assert not card.save() and card.message.text().startswith("The proposal line must be at least 40")
    card.check()
    assert card.regression.text() == "No labels are saved yet."


@pytest.fixture
def pop_window(qtbot, qapp, tmp_path):
    s = K.population_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    dp = FakeDpapi()
    w.bridge.dpapi = (dp.protect, dp.unprotect)
    w.settings.open_()
    w.refresh()
    settle(qapp)
    return w, s, dp


def test_measure_is_held_until_a_real_run(qtbot, qapp, tmp_path):
    from tests.support.example_session import example_session
    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    w.refresh()
    b = w.m13.measure.open_button
    assert b.held and b.caption.text() == "Held until a run that isn't practice has finished."


@pytest.mark.claim("CL-CAL-NOSCORE-01")
@pytest.mark.claim("CL-CAL-KNOWN-01")
@pytest.mark.claim("CL-CAL-NOCHANGE-01")
def test_the_matching_window_end_to_end(pop_window, qtbot, qapp):
    w, s, dp = pop_window
    before = (s.results.digest(), len(s.history.stack), set(s.stale), s.thresholds)
    card = w.m13.measure
    assert not card.open_button.held
    mw = card.open_window()
    assert (mw.width(), mw.height()) == (1100, 720)
    mw.per_band.setValue(3)
    run_job(qtbot, qapp, w, lambda: mw.draw())
    cal = mw.cal
    total = len(cal.pairs)
    lv = mw.labeler
    assert lv.findChild(QLabel, "labelNoScore").text() == copy.get("matching.label.no_score")
    assert lv.start("Ana")
    settle(qapp)
    pairs_score = {str(p.score) for p in cal.pairs}
    shown = visible_texts(lv)
    assert not set(shown) & pairs_score
    assert not any(re.search(r"\bband\b|\bscore\b|exact|nickname|dob_", t, re.I) for t in shown
                   if t != copy.get("matching.label.no_score"))
    for i in range(total):
        qtbot.keyClick(lv, (Qt.Key_S, Qt.Key_D, Qt.Key_U)[i % 3])
    assert lv.bar.value() == lv.bar.maximum() == total
    assert set(cal.labels_for("Ana").values()) <= {"same", "different", "unsure"}
    lv.hand_over()
    assert not lv.start("ana ") and lv.message.text() == copy.get("calibration.refused.labeler_same_person")
    assert lv.start("Ben")
    for p in cal.pairs:
        lv.choose("same" if p.score >= 80 or p.kind == "join" else "different")
    lv.hand_over()
    settle(qapp)
    assert cal.both_finished() and mw.stack.currentIndex() == 2
    for pid in list(cal.disagreements()):
        cal.settle(pid, "different")
    mw.go(3)
    assert mw.findChild(QLabel, "knownNote").text() == copy.get("matching.known.note", n=50)
    from PySide6.QtWidgets import QTableWidgetItem
    for c, v in enumerate(("people_a", "PA0000", "people_b", "PB0000")):
        mw.known.setItem(0, c, QTableWidgetItem(v))
    res = mw.check_known()
    assert res.entered == 1 and res.not_in_batch == 0
    mw.go(4)
    assert mw.findChild(QLabel, "resultSuggested") is not None
    n = mw.save()
    assert n > 0 and (s.calibration_dir / "labeled.wcl").exists() and not (s.calibration_dir / "draft.wcl").exists()
    # Measuring changes no weight, no line, no decision and no result.
    assert (s.results.digest(), len(s.history.stack), set(s.stale), s.thresholds) == before
    raw = (s.calibration_dir / "labeled.wcl").read_bytes()
    assert b"PA0000" not in raw and b"PA0000" not in dp.unprotect(raw[4:])


def test_every_new_control_is_held_during_a_run(xwin, qapp):
    w, s = xwin()
    w.run_hold.hold()
    settle(qapp)
    from wholecount.ui.widgets.held import HeldAction
    for c in w.m13.cards:
        for h in c.findChildren(HeldAction):
            assert h.held, h.objectName()
        for sb in c.findChildren(QSpinBox):
            assert sb in w.run_hold.registered(), sb.objectName()
    w.run_hold.release()


@pytest.mark.parametrize("width", [1280, 1366, 1440, 1920])
def test_the_drawer_fits_every_width(xwin, qapp, width):
    w, s = xwin()
    w.resize(width, 900)
    w.settings.open_()
    settle(qapp)
    sb = w.settings.scroll.horizontalScrollBar()
    assert sb.maximum() == 0
    for c in w.m13.cards:
        assert c.width() <= w.settings.panel.width()


@pytest.mark.claim("CL-XW-DATALINE-01")
@pytest.mark.claim("CL-XW-YOURDATA-01")
def test_the_data_line_and_your_data_mention_the_crosswalk_only_while_on(xwin, qapp):
    w, s = xwin()
    w.go_to("export")
    w.refresh()
    settle(qapp)
    writes = w.stage_widget.head.dataline.text("writes")
    assert "crosswalk" not in writes and copy.get("yourdata.crosswalk") not in texts(w.your_data)
    X.turn_on(s)
    w.refresh()
    settle(qapp)
    assert w.stage_widget.head.dataline.text("writes").endswith(copy.get("dataline.note.export.crosswalk"))
    assert copy.get("yourdata.crosswalk") in texts(w.your_data)
    # What it says matches the file: the table names hold keys, IDs and decisions only.
    import sqlite3
    con = sqlite3.connect(str(s.crosswalk_path))
    cols = {r[1] for t in ("person", "person_key", "pair_verdict", "program_group") for r in con.execute(f"PRAGMA table_info({t})")}
    con.close()
    assert not cols & {"name", "first_name", "last_name", "address", "dob", "client_id"}


def test_every_band_sentence_renders():
    from wholecount.ui.settings.matching import _band_text
    for b in (1, 2, 3, 4):
        assert _band_text("matching.draw.band", b, n=3)
        assert _band_text("matching.results.band", b, same=1, labeled=2, population=9)
        assert _band_text("matching.results.unmeasured", b, population=9)
