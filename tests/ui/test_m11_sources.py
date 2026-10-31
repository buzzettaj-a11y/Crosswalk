"""Add your files (M11 section 1): the fast path and its holds, example data, notices, systems, the table list and the
rows accounted for, checked against the example files' EXPECTED.json."""
import dataclasses

import pytest
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit

from tests.support.m11 import EXPECTED, empty_session, example_window, last, run_job, window_for, write_csv
from tests.ui.conftest import Confirm, settle
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.survey import survey
from wholecount.ui.stages.sources.body import fast_path_holds


def texts(w):
    return " ".join(x.text() for x in w.findChildren(QLabel) if x.isVisibleTo(w))


@pytest.mark.claim("CL-HOLD-NOTABLE-01")
def test_held_until_a_table_is_included(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path)
    for t in survey(s).tables:
        if t.included:
            s.history.execute(C.SetupChange("tables", (t.file_name, t.idx, "included"), False))
    w.refresh()
    body = w.stage_widget
    assert body.process_all.hold.text == "Held until at least one table is included."
    assert body.process_all.button.property("kind") == "held" and body.process_all.caption.isVisible()
    started = w.bridge.runner.threads_started
    body.process_all.button.click()
    assert w.bridge.runner.threads_started == started


@pytest.mark.claim("CL-HOLD-BLOCKER-01")
@pytest.mark.claim("CL-HOLD-BLOCKER-02")
def test_held_until_the_required_column_is_matched(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path)
    s.history.execute(C.SetupChange("mappings", ("example_clinic.csv", 0, "First_Name"), ""))
    w.refresh()
    assert w.stage_widget.process_all.hold.text == "Held until example_clinic.csv has a column for First_Name."
    assert [b.field for b in survey(s).blocks] == ["First_Name"]
    s.history.execute(C.SetupChange("mappings", ("example_partner.tsv", 0, "Last_Name"), ""))
    w.refresh()
    assert w.stage_widget.process_all.hold.text == "Held until example_clinic.csv has a column for First_Name, and 1 more."
    s.history.execute(C.SetupChange("mappings", ("example_clinic.csv", 0, "Zip"), ""))
    w.refresh()
    assert "Zip" not in w.stage_widget.process_all.hold.text


@pytest.mark.claim("CL-HOLD-ACCOUNTED-01")
@pytest.mark.claim("CL-ACCOUNTED-01")
def test_rows_accounted_for_match_expected_and_hold_when_not(qtbot, qapp, tmp_path, monkeypatch):
    w, s = example_window(qtbot, qapp, tmp_path)
    sv = survey(s)
    for f in sv.files:
        e = EXPECTED["files"][f.name]
        after = e.get("after_header_choice")      # the example session applies the planned header row
        got = (f.in_tables, f.above_header, f.header_rows)
        if after:
            assert got == (after["rows_included"], after["rows_above_header"], after["rows_header"])
        else:
            assert got == (e["rows_included"], e["rows_above_header"], e["rows_header"])
            assert (f.in_excluded, f.not_tables) == (e["rows_excluded"], e["rows_non_table"])
        assert f.total == e["non_empty_rows"] + e["rows_shared"] and f.balanced
    card = w.stage_widget.findChild(QLabel, "accountedBatch")
    assert card is not None and str(sum(f.total for f in sv.files)) in card.text().replace(",", "")
    bad = dataclasses.replace(sv.files[0], total=sv.files[0].total + 1)
    broken = dataclasses.replace(sv, files=(bad,) + sv.files[1:])
    assert fast_path_holds(broken)[0].text == "Held until every row in every file is accounted for."
    monkeypatch.setattr(type(w.bridge), "survey", lambda self: broken)
    w.refresh()
    settle(qapp)
    assert copy.get("src.accounted.wrong") in texts(w)


@pytest.mark.claim("CL-FAST-PROGRAMS-01")
def test_fast_path_stops_at_programs_then_runs_and_lands_on_review(qtbot, qapp, tmp_path):
    from tests.support.example_session import PLAN

    w, s = example_window(qtbot, qapp, tmp_path)
    n = len(survey(s).program_map.unconfirmed)
    assert n
    w.stage_widget.process_all.button.click()
    settle(qapp)
    assert w.current == "programs" and w.bridge.runner.threads_started == 0
    assert w.findChild(QLabel, "programNotice").text() == copy.get("src.fast.programs", n=n)
    for g in PLAN["decisions"]["program_groups"]:
        s.history.execute(C.DecideProgramGroup("confirm", tuple(g["names"]), g["label"]))
    w.go_to("sources")
    run_job(qtbot, qapp, w, lambda: (w.stage_widget.process_all.button.click(), True)[1])
    assert w.current == "review"


@pytest.mark.claim("CL-EXAMPLE-FAKE-01")
@pytest.mark.claim("CL-PRACTICE-01")
def test_example_data_is_practice_at_once_and_start_over_clears_it(qtbot, qapp, tmp_path):
    s = empty_session(tmp_path)
    w = window_for(qtbot, qapp, s)
    assert not w.topbar.practice.isVisible()
    w.stage_widget.zone.example.button.click()
    settle(qapp)
    assert w.topbar.practice.isVisible()
    assert w.stage_widget.findChild(type(w.stage_widget.fast), "exampleNotice") is not None
    assert w.bridge.session.backend.name == "reference_sample" and w.bridge.session.allow_sample
    assert len(w.bridge.session.setup.paths()) == 5
    from wholecount.session.runner import process

    assert process(w.bridge.session).practice is True
    w.request_start_over()
    w.bridge.ui.pop("practice", None)
    w.bridge.ui.pop("example_loaded", None)
    w.refresh()
    assert not w.topbar.practice.isVisible()


def test_own_files_never_get_the_sample_reference(qtbot, qapp, tmp_path):
    s = empty_session(tmp_path)
    w = window_for(qtbot, qapp, s)
    p = write_csv(tmp_path / "mine.csv", ["First Name", "Last Name", "Client ID"], [["Ana", "Lee", "1"]])
    run_job(qtbot, qapp, w, lambda: w.add_files([p]))
    assert s.backend.name == "none" and not s.allow_sample
    assert not w.topbar.practice.isVisible()


def test_notices_encoding_and_sensitive(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path)
    enc = w.stage_widget.findChild(type(w.stage_widget.fast), "encoding")
    assert enc is not None
    samples = [x for x in enc.findChildren(QLabel) if x.property("role") == "caption"]
    assert 0 < len(samples) <= 5
    sv = survey(s)
    assert ("SSN", "name") in next(f for f in sv.files if f.name == "example_partner.tsv").sensitive
    assert all("SSN" not in t.headers for t in sv.loaded.values())


@pytest.mark.claim("CL-SENSITIVE-KEEP-01")
def test_unticking_a_sensitive_column_asks_then_reads_again(qtbot, qapp, tmp_path):
    c = Confirm(False)
    w, s = example_window(qtbot, qapp, tmp_path, confirm=c)
    box = next(b for b in w.stage_widget.findChildren(QCheckBox) if "SSN" in b.text())
    box.setChecked(False)
    settle(qapp)
    assert c.asked and "Keep SSN in memory?" in c.asked[-1][1][0]
    assert "SSN" not in s.keep_sensitive
    c.answer = True
    box = next(b for b in w.stage_widget.findChildren(QCheckBox) if "SSN" in b.text())
    box.setChecked(False)
    settle(qapp)
    assert isinstance(last(s), C.SetKeepSensitive) and last(s).keep
    assert any("SSN" in t.headers for t in survey(s).loaded.values())
    # kept in memory but matched to nothing, so it reaches no download (H10)
    assert all(w_.mapping.column_for(f) is None or w_.mapping.column_for(f).name != "SSN"
               for w_ in survey(s).works.values() for f in ("Client_ID", "First_Name"))


def test_a_bad_file_shows_its_card_while_the_others_load(qtbot, qapp, tmp_path):
    s = empty_session(tmp_path)
    w = window_for(qtbot, qapp, s)
    good = write_csv(tmp_path / "good.csv", ["First Name", "Last Name", "Client ID"], [["Ana", "Lee", "1"]])
    bad = tmp_path / "broken.xlsx"
    bad.write_bytes(b"not a workbook")
    run_job(qtbot, qapp, w, lambda: w.add_files([good, bad]))
    assert w.stage_widget.findChild(type(w.stage_widget.fast), "unreadable") is not None
    assert [t.file_name for t in survey(s).tables] == ["good.csv"]


def test_the_same_file_again_changes_nothing(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path)
    before = list(s.setup.paths())
    assert w.add_files([before[0]]) is False
    settle(qapp)
    assert list(s.setup.paths()) == before
    assert "is already added." in texts(w)


@pytest.mark.claim("CL-CORRECTIONS-RECOGNIZED-01")
@pytest.mark.claim("CL-CORRECTIONS-RECOGNIZED-02")
def test_a_review_file_sent_back_is_corrections_not_a_source(qtbot, qapp, tmp_path):
    s = empty_session(tmp_path)
    w = window_for(qtbot, qapp, s)
    good = write_csv(tmp_path / "good.csv", ["First Name", "Last Name", "Client ID"], [["Ana", "Lee", "1"]])
    back = write_csv(tmp_path / "Manual_Review_Needed.csv", ["Record_Key", "Run_ID", "Signature", "Corrected_Zip"],
                     [["k1", "r1", "s1", "11201"]])
    run_job(qtbot, qapp, w, lambda: w.add_files([good, back]))
    assert [p.name for p in s.setup.paths()] == ["good.csv"]
    assert copy.get("src.corrections_file", name="Manual_Review_Needed.csv") in texts(w)


def test_table_ticks_remove_and_systems_fire_commands(qtbot, qapp, tmp_path):
    w, s = example_window(qtbot, qapp, tmp_path)
    box = w.stage_widget.findChild(QCheckBox, "include_A_0")
    box.setChecked(False)
    settle(qapp)
    cmd = last(s)
    assert isinstance(cmd, C.SetupChange) and (cmd.section, cmd.key, cmd.new) == (
        "tables", ("example_clinic.csv", 0, "included"), False)
    sel = w.stage_widget.findChild(QComboBox, "system_B")
    sel.setCurrentIndex(sel.findData("example_clinic.csv"))
    settle(qapp)
    assert (last(s).section, last(s).key, last(s).new) == ("systems", ("member", "example_housing.xlsx"), "example_clinic.csv")
    name = w.stage_widget.findChild(QLineEdit, "system_name_A")
    name.setText("Clinic system")
    name.editingFinished.emit()
    settle(qapp)
    assert (last(s).key, last(s).new) == (("name", "example_clinic.csv"), "Clinic system")
    rm = w.stage_widget.findChild(type(w.stage_widget.process_all), "remove_C")
    rm.button.click()
    settle(qapp)
    assert last(s).section == "sources" and last(s).new is False and "example_partner.tsv" in last(s).key


@pytest.mark.claim("CL-SYSTEMS-01")
def test_client_ids_join_only_inside_one_system(tmp_path):
    from tests.support.example_session import example_session
    from wholecount.session.runner import process

    s = example_session(tmp_path)
    r = s.results
    for j in r.identity.auto_joins:
        if j.reason == "same_system_id":
            a, b = j.pair
            sa = {r.system_of_record[k] for k in r.rows if r.identity.master_of_record.get(k) and k in (a, b)}
            assert len(sa) <= 1
    s.history.execute(C.SetupChange("systems", ("member", "example_housing.xlsx"), "example_clinic.csv"))
    r2 = process(s)
    sysnames = {r2.file_of_record[k]: r2.system_of_record[k] for k in r2.rows}
    assert sysnames["example_housing.xlsx"] == sysnames["example_clinic.csv"]


def test_adding_fifteen_files_shows_both_steps_and_no_client_value(qtbot, qapp, tmp_path):
    from wholecount.ui.frame import a11y

    s = empty_session(tmp_path)
    w = window_for(qtbot, qapp, s)
    paths = [write_csv(tmp_path / f"f{i:02d}.csv", ["First Name", "Last Name", "Client ID"],
                       [["Quorvath", f"Zelphina{i}", f"C{i}"]]) for i in range(15)]
    fractions = []
    w.bridge.runner.progressed.connect(lambda snap: fractions.append(w.ticker.fraction))
    a11y.ANNOUNCED.clear()
    run_job(qtbot, qapp, w, lambda: w.add_files(paths))
    assert a11y.ANNOUNCED[:2] == ["Reading files", "Finding tables"]
    assert fractions == sorted(fractions)
    seen = " ".join(a11y.ANNOUNCED) + w.ticker.left.text() + w.ticker.full_message
    assert "Quorvath" not in seen and "Zelphina" not in seen
    assert len(s.setup.paths()) == 15


@pytest.mark.claim("CL-RESUME-MATCH-01")
@pytest.mark.claim("CL-RESUME-CHANGED-01")
def test_resume_matches_files_by_contents_and_flags_a_changed_one(qtbot, qapp, tmp_path):
    from tests.fixtures.session import r_fixture
    from tests.support.fake_dpapi import FakeDpapi
    from tests.support.session import rk
    from wholecount.session.runner import process
    from wholecount.session.store import Store

    fd = FakeDpapi()
    store = Store(tmp_path / "store", fd.protect, fd.unprotect)
    first = r_fixture.session(tmp_path / "a")
    process(first)
    first.store = store
    first.history.execute(C.SetAsideRows([rk(first, "R14")], "out_of_scope"))
    saved_r = tmp_path / "a" / "R.csv"
    copies = tmp_path / "again"
    copies.mkdir()
    r_copy = copies / "R.csv"
    r_copy.write_bytes(saved_r.read_bytes())
    s_copy = copies / "S.csv"
    s_copy.write_bytes((tmp_path / "a" / "S.csv").read_bytes() + b"Zed,Changed,,,,,,\n")
    fresh = empty_session(tmp_path / "b")
    fresh.session_id = "fresh"            # the fixture's clock gives both sessions one ID
    fresh.store = store
    w = window_for(qtbot, qapp, fresh)
    entries = w.bridge.saved_progress_entries()
    assert len(entries) == 1 and entries[0]["decisions"] == 1
    run_job(qtbot, qapp, w, lambda: w.resume(entries[0], [r_copy, s_copy]))
    plan = w.bridge.ui["resume_plan"]
    assert plan.restored == ("R.csv",) and plan.changed == ("S.csv",)
    assert plan.kept == 1
    assert w.stage_widget.findChild(type(w.stage_widget.fast), "resumeChanged") is not None
