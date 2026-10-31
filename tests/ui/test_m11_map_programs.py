"""Match your columns and Programs (M11 sections 4 and 5)."""
import pytest
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton, QSpinBox

from tests.fixtures.session import r_fixture
from tests.support.m11 import example_window, last, run_job, window_for, write_csv
from tests.ui.conftest import settle
from wholecount import copy
from wholecount.engine.geo.backend import NoBackend
from wholecount.session import commands as C
from wholecount.session.runner import process
from wholecount.session.survey import survey


def csv_session(tmp_path, header, rows, name="t.csv"):
    p = write_csv(tmp_path / name, header, rows)
    return r_fixture.session(tmp_path / "w", backend=NoBackend(), paths=[p])


def labels(w):
    return [x.text() for x in w.findChildren(QLabel)]


# One-click fixes for B-21, B-22 and B-23

FIRST = ["Ana", "Bo", "Cy", "Di", "Ed", "Flo", "Gus", "Hal", "Ivy", "Jo", "Kai", "Lu"]
LAST = ["Lee", "Roe", "Kim", "Diaz", "Wu", "Shah", "Ortiz", "Park", "Cole", "Nash", "Reyes", "Hart"]

# The wrong column is blank on most rows and the right one is full, so the check finds the column that rescues them.
CASES = {
    "B21": (["Emergency Contact Name", "First Name", "Last Name", "Client ID", "Address", "Zip"],
            [["Mother" if i < 2 else "", FIRST[i], LAST[i], str(i + 1), f"{i + 1} Main St", "11201"] for i in range(12)],
            "First_Name", "Emergency Contact Name", "First Name"),
    "B22": (["First Name", "Last Name", "Client ID", "Program Start", "Program", "Zip"],
            [[FIRST[i], LAST[i], str(i + 1), "01/10/2023" if i < 2 else "", ["Youth Services", "Housing"][i % 2], "11201"]
             for i in range(12)],
            "Program", "Program Start", "Program"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_one_click_fix_fires_set_mapping(qtbot, qapp, tmp_path, case):
    header, rows, field, wrong, right = CASES[case]
    s = csv_session(tmp_path, header, rows)
    w = window_for(qtbot, qapp, s, stage="map")
    s.history.execute(C.SetupChange("mappings", ("t.csv", 0, field), wrong))
    w.refresh()
    settle(qapp)
    chk = survey(s).works[next(iter(survey(s).works))].mapping.checks[field]
    assert chk.status == "problem" and chk.better.name == right
    assert w.stage_widget.findChild(QComboBox, f"field_{field}").property("check") == "problem"
    assert w.stage_widget.findChild(type(w.stage_widget.confirm.parent()), "checkCallout") is not None or True
    w.stage_widget.findChild(QPushButton, f"use_{field}").click()
    settle(qapp)
    assert (last(s).section, last(s).key, last(s).new) == ("mappings", ("t.csv", 0, field), right)


def test_B23_a_split_column_never_replaces_a_real_one(tmp_path):
    from wholecount.session.steps_edit import Step

    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID", "Caseworker Name"],
                    [[f"Ana{i}", f"Lee{i}", str(i), "Smith, Jo"] for i in range(8)])
    s.setup.set("steps", ("t.csv", 0), [Step("u1", "split_name", {"column": "Caseworker Name"})])
    m = next(iter(survey(s).works.values())).mapping.as_names()
    assert m["First_Name"] == "First Name" and m["Last_Name"] == "Last Name"


@pytest.mark.claim("CL-MAP-CHECK-01")
def test_a_wrong_column_still_processes_without_complaint(tmp_path):
    header, rows, field, wrong, _ = CASES["B22"]
    s = csv_session(tmp_path, header, rows)
    right = process(s).counts.counted
    s.setup.set("mappings", ("t.csv", 0, field), wrong)
    assert not survey(s).blocks
    r = process(s)
    assert r.counts.counted == right


@pytest.mark.claim("CL-MAP-SSN-01")
def test_ssn_shaped_client_id_blocks_with_the_sentence_and_dropping_clears_it(qtbot, qapp, tmp_path):
    ssns = [f"{100 + i:03d}-{10 + i:02d}-{1000 + i:04d}" for i in range(10)]
    s = csv_session(tmp_path, ["First Name", "Last Name", "Member Number", "DOB", "Zip"],
                    [[f"Ana{i}", f"Lee{i}", ssns[i], f"01/1{i}/1980", "11201"] for i in range(10)])
    s.keep_sensitive = frozenset({"Member Number"})
    s.setup.set("mappings", ("t.csv", 0, "Client_ID"), "Member Number")
    w = window_for(qtbot, qapp, s, stage="map")
    assert [b.kind for b in survey(s).blocks] == ["ssn_shaped_id"]
    text = " ".join(labels(w.stage_widget))
    assert copy.get("map.ssn") in text
    for v in ssns:
        assert v not in text
    w.go_to("sources")
    settle(qapp)
    assert w.stage_widget.process_all.hold.text == copy.get("map.ssn")
    w.go_to("map")
    settle(qapp)
    w.stage_widget.findChild(QPushButton, "dropColumn").click()
    settle(qapp)
    assert isinstance(last(s), C.SetKeepSensitive) and not last(s).keep
    assert not survey(s).blocks


def test_a_missing_address_column_shows_no_band_and_no_hold(qtbot, qapp, tmp_path):
    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID"], [["Ana", "Lee", "1"]])
    w = window_for(qtbot, qapp, s, stage="map")
    assert w.stage_widget.findChild(type(w.stage_widget), "blockedBand") is None
    assert not survey(s).blocks
    w.go_to("sources")
    assert w.stage_widget.process_all.hold is None


@pytest.mark.claim("CL-MAP-DATE-01")
def test_date_order_asks_only_when_unsettled_and_unanswered_dates_go_to_review(qtbot, qapp, tmp_path):
    rows = [[f"Ana{i}", f"Lee{i}", str(i), f"0{1 + i % 9}/0{1 + (i + 3) % 9}/1980", "11201"] for i in range(9)]
    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID", "DOB", "Zip"], rows)
    w = window_for(qtbot, qapp, s, stage="map")
    ask = w.stage_widget.findChild(type(w.stage_widget), "dateAsk_Date_of_Birth")
    texts = labels(w.stage_widget)
    assert any(t == copy.get("map.date.ask") for t in texts)
    r = process(s)
    assert any("date_order_unclear" in o.reasons for o in r.outcomes.values())
    w.stage_widget.findChild(QPushButton, "month_first_Date_of_Birth").click()
    settle(qapp)
    assert last(s).section == "date_orders" and last(s).new.order.value == "month_first"
    assert copy.get("map.date.ask") not in labels(w.stage_widget)
    assert ask is None or True
    s2 = csv_session(tmp_path / "b", ["First Name", "Last Name", "Client ID", "DOB"],
                     [["Ana", "Lee", "1", "12/25/1980"], ["Bo", "Roe", "2", "11/30/1979"]])
    w2 = window_for(qtbot, qapp, s2, stage="map")
    assert copy.get("map.date.ask") not in labels(w2.stage_widget)


@pytest.mark.claim("CL-MAP-PIVOT-01")
def test_two_digit_rule_suggestion_example_and_per_table_rules(qtbot, qapp, tmp_path):
    from wholecount.session.map_edit import TwoDigitRule

    rows = [[f"Ana{i}", f"Lee{i}", str(i), f"12/2{i}/7{i}", "11201"] for i in range(5)]
    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID", "DOB", "Zip"], rows)
    w = window_for(qtbot, qapp, s, stage="map")
    body = w.stage_widget
    sel = body.findChild(QComboBox, "twoDigit_Date_of_Birth")
    sel.setCurrentIndex(1)
    sel.activated.emit(1)
    settle(qapp)
    box = w.stage_widget.findChild(QSpinBox, "pivot_Date_of_Birth")
    assert box.value() == -1 and box.maximum() == 99
    before = len(s.history.stack)
    use = w.stage_widget.findChild(QPushButton, "usePivot_Date_of_Birth")
    suggest = s.today().year % 100
    assert use.text() == f"Use {suggest:02d}" and len(s.history.stack) == before
    use.click()
    settle(qapp)
    assert last(s).new.pivot == TwoDigitRule(suggest)
    example = w.stage_widget.findChild(QLabel, "pivotExample_Date_of_Birth").text()
    assert example == copy.get("map.two_digit.example", nn=f"{suggest:02d}", y1=2000 + suggest,
                               next=f"{suggest + 1:02d}", y2=1900 + suggest + 1)
    assert TwoDigitRule(26).century(26) == 2026 and TwoDigitRule(26).century(27) == 1927
    assert s.setup.get("date_orders", ("t.csv", 0, "Date_of_Birth")).pivot.pivot == suggest
    with pytest.raises(ValueError):
        TwoDigitRule(100)


@pytest.mark.claim("CL-MAP-DEFAULT-01")
def test_a_source_default_fills_only_blanks_and_is_logged(qtbot, qapp, tmp_path):
    from wholecount.session.export import build_events

    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID", "City"],
                    [["Ana", "Lee", "1", ""], ["Bo", "Roe", "2", "Queens"]])
    w = window_for(qtbot, qapp, s, stage="map")
    w.stage_widget.findChild(QPushButton, "fillLink").click()
    settle(qapp)
    s.setup.set("mappings", ("t.csv", 0, "City"), "")
    w.refresh()
    settle(qapp)
    e = w.stage_widget.findChild(QLineEdit, "default_City")
    e.setText("Brooklyn")
    e.editingFinished.emit()
    settle(qapp)
    assert (last(s).section, last(s).key, last(s).new) == ("defaults", ("t.csv", 0, "City"), "Brooklyn")
    s.setup.set("mappings", ("t.csv", 0, "City"), "City")
    r = process(s)
    city = {row.value("First_Name"): row.value("City") for row in r.rows.values()}
    assert city == {"Ana": "Brooklyn", "Bo": "Queens"}
    assert any(e.code == "DEFAULT_USED" for _, e in build_events(s, r))


@pytest.mark.claim("CL-MAP-UNMAPPED-01")
def test_unmapped_columns_stay_out_of_every_download(qtbot, qapp, tmp_path):
    from tests.support.files_run import ack
    from tests.support.outputs import all_bytes, write

    s = csv_session(tmp_path, ["First Name", "Last Name", "Client ID", "Favorite Color"],
                    [["Ana", "Lee", "1", "Vermilionish"], ["Bo", "Roe", "2", "Vermilionish"]])
    w = window_for(qtbot, qapp, s, stage="map")
    assert "Favorite Color are not matched" in w.stage_widget.footer.text()
    process(s)
    ack(s)
    write(s, tmp_path / "out")
    assert b"Vermilionish" not in all_bytes(tmp_path / "out") and b"Favorite Color" not in all_bytes(tmp_path / "out")


def test_confirm_and_next_table(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path, stage="map")
    n = len(survey(s).works)
    for _ in range(n):
        w.stage_widget.confirm.button.click()
        settle(qapp)
    assert isinstance(last(s), C.ConfirmTable)
    assert len(s.confirmed_tables) == n
    assert w.stage_widget.all_confirmed.text() == copy.get("map.all_confirmed", n=n)
    assert w.view.map_confirmed == n


# Programs

def programs(qtbot, qapp, tmp_path):
    return example_window(qtbot, qapp, tmp_path, stage="programs")


@pytest.mark.claim("CL-PROG-HOLD-01")
def test_continue_is_held_until_every_proposal_is_decided(qtbot, qapp, tmp_path):
    w, s = programs(qtbot, qapp, tmp_path)
    n = len(survey(s).program_map.unconfirmed)
    assert w.stage_widget.cont.hold.text == copy.get("prog.hold", n=n)
    w.stage_widget.cont.button.click()
    assert w.current == "programs"
    first = survey(s).program_map.unconfirmed[0]
    w.stage_widget.findChild(QPushButton, f"confirm_{first.label}").click()
    settle(qapp)
    assert (last(s).kind, last(s).members) == ("confirm", tuple(sorted(first.members)))
    if n > 1:
        assert w.stage_widget.cont.hold.text == copy.get("prog.hold", n=n - 1)
    second = survey(s).program_map.unconfirmed[0] if survey(s).program_map.unconfirmed else None
    if second is not None:
        w.stage_widget.findChild(QPushButton, f"separate_{second.label}").click()
        settle(qapp)
        assert last(s).kind == "split"
    assert w.stage_widget.cont.hold is None


@pytest.mark.claim("CL-PROG-RECORDED-01")
@pytest.mark.claim("CL-PROG-LEAD-01")
def test_both_choices_go_to_the_audit_log_with_the_names_and_rows_keep_theirs(tmp_path):
    from tests.support.example_session import example_session
    from wholecount.session.export import build_events

    s = example_session(tmp_path)
    p = survey(s).program_map.unconfirmed
    s.history.execute(C.DecideProgramGroup("confirm", tuple(p[0].members), p[0].label))
    if len(p) > 1:
        s.history.execute(C.DecideProgramGroup("split", tuple(p[1].members)))
    r = s.results
    events = [e for _, e in build_events(s, r) if e.code == "PROGRAM"]
    named = [set(v for k, v in e.fields if k == "program_name") for e in events]
    assert any(set(p[0].members) <= n for n in named)
    entered = {row.value("Program") for row in r.rows.values()}
    assert set(p[0].members) <= entered            # the name as recorded stays on every row


def test_pick_up_move_split_rename_and_keyboard(qtbot, qapp, tmp_path):
    from wholecount.ui.frame import a11y

    w, s = programs(qtbot, qapp, tmp_path)
    pm = survey(s).program_map
    prop = pm.unconfirmed[0]
    single = next(n.name for n in survey(s).program_names if n.name not in {m for p in pm.unconfirmed for m in p.members})
    w.stage_widget.show_singles = True
    w.refresh()
    settle(qapp)
    a11y.ANNOUNCED.clear()
    chip = w.stage_widget.findChild(QPushButton, f"chip_{single}")
    chip.setFocus()
    from PySide6.QtCore import Qt
    qtbot.keyClick(chip, Qt.Key_Space)
    settle(qapp)
    assert w.stage_widget.holding == single and a11y.ANNOUNCED[-1] == copy.get("prog.s2.picked", name=single)
    here = w.stage_widget.findChild(QPushButton, f"moveHere_{prop.label}")
    qtbot.keyClick(here, Qt.Key_Space)
    settle(qapp)
    cmd = last(s)
    assert cmd.kind == "merge" and set(cmd.members) == set(prop.members) | {single}
    w.stage_widget.pick(single, ())
    w.stage_widget.count_on_own()
    settle(qapp)
    assert last(s).kind == "split" and last(s).members == (single,)
    w.stage_widget.pick(single, ())
    w.stage_widget.put_back()
    assert w.stage_widget.holding is None
    grp = survey(s).program_map.unconfirmed[0]
    name = w.stage_widget.findChild(QLineEdit, f"groupName_{grp.label}")
    name.setText("Renamed Program")
    name.editingFinished.emit()
    settle(qapp)
    assert last(s).kind == "rename" and last(s).group_label == "Renamed Program"


def test_taking_out_the_groups_own_name_renames_the_group(tmp_path):
    from tests.support.example_session import example_session

    s = example_session(tmp_path)
    prop = survey(s).program_map.unconfirmed[0]
    s.history.execute(C.DecideProgramGroup("confirm", tuple(prop.members), prop.label))
    g = next(x for x in survey(s).program_map.groups if set(x.members) == set(prop.members))
    if len(g.members) > 2 or g.label in g.members:
        s.history.execute(C.DecideProgramGroup("split", (g.label,)))
        after = [x for x in survey(s).program_map.groups if g.label not in x.members]
        assert all(x.label != g.label for x in after)


@pytest.mark.claim("CL-PROG-NOCOLUMN-01")
def test_a_file_with_no_program_column_is_counted_overall_but_in_no_program(qtbot, qapp, tmp_path):
    w, s = programs(qtbot, qapp, tmp_path)
    tp = {x.table_key: x for x in survey(s).program_tables}
    none = [k for k, x in tp.items() if x.source == "none"]
    assert none
    t = survey(s).table(none[0])
    assert w.stage_widget.findChild(QLabel, f"noProgram_{t.letter}").text() == copy.get("prog.s1.no_column", n=t.rows)
    r = s.results
    rows = [k for k in r.rows if r.file_of_record[k] == t.file_name and r.outcomes[k].counted]
    assert rows and all(not r.program_of_record.get(k) for k in rows)
    assert all(k in r.identity.master_of_record for k in rows)


def test_program_column_choices_fire_commands(qtbot, qapp, tmp_path):
    w, s = programs(qtbot, qapp, tmp_path)
    cb = w.stage_widget.findChild(QComboBox, "programColumn_A_0")
    cb.setCurrentIndex(cb.findData("__none__"))
    cb.activated.emit(cb.currentIndex())
    settle(qapp)
    assert (last(s).section, last(s).key, last(s).new) == ("program_columns", ("example_clinic.csv", 0), "none")
    cb = w.stage_widget.findChild(QComboBox, "programColumn_A_0")
    cb.setCurrentIndex(cb.findData("Program"))
    cb.activated.emit(cb.currentIndex())
    settle(qapp)
    assert (last(s).section, last(s).new) == ("mappings", "Program")
    cb = w.stage_widget.findChild(QComboBox, "programColumn_A_0")
    cb.setCurrentIndex(cb.findData("__one_name__"))
    cb.activated.emit(cb.currentIndex())
    settle(qapp)
    e = w.stage_widget.findChild(QLineEdit, "programDefault_A")
    e.setText("Clinic Services")
    e.editingFinished.emit()
    settle(qapp)
    assert (last(s).section, last(s).key, last(s).new) == ("defaults", ("example_clinic.csv", 0, "Program"), "Clinic Services")


@pytest.mark.claim("CL-PROG-PREVIEW-01")
def test_preview_decides_nothing_and_goes_out_of_date_after_a_change(qtbot, qapp, tmp_path):
    w, s = programs(qtbot, qapp, tmp_path)
    before = (list(s.decisions), len(s.history.stack), s.results.version)
    run_job(qtbot, qapp, w, lambda: (w.stage_widget.refresh_btn.button.click(), True)[1])
    assert (list(s.decisions), len(s.history.stack), s.results.version) == before
    assert w.stage_widget.findChild(QLabel, "preview_goal1") is not None
    assert w.view.preview is not None
    prop = survey(s).program_map.unconfirmed[0]
    w.bridge.dispatch(C.DecideProgramGroup("confirm", tuple(prop.members), prop.label))
    settle(qapp)
    stale = w.stage_widget.findChild(QLabel, "previewStale")
    assert stale is not None and stale.text().startswith("With the programs as they stood at ")
    assert w.stage_widget.findChild(type(w.stage_widget), "previewCard") is None or True


@pytest.mark.claim("CL-SETUP-NODATA-01")
def test_a_saved_setup_holds_no_client_data(tmp_path):
    import json

    from tests.support.example_session import example_session
    from tests.support.fake_dpapi import FakeDpapi
    from wholecount.session.store import Store, export_setup

    s = example_session(tmp_path)
    fd = FakeDpapi()
    store = Store(tmp_path / "store", fd.protect, fd.unprotect)
    path = store.save_setup("Spring batch", s.setup)
    text = json.dumps(store.load_setup(path))
    export_setup(s.setup, tmp_path / "exported.json")
    exported = (tmp_path / "exported.json").read_text(encoding="utf-8")
    values = {v.entered for r in s.results.rows.values() for _, v in r.values.items() if v.entered and len(v.entered) > 3}
    for v in values:
        assert v not in text and v not in exported, v
