"""Your columns and Tidy up (M11 sections 2 and 3)."""
import pytest
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton

from tests.support.m11 import example_window, last
from tests.ui.conftest import Confirm, settle
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.schema_edit import Field, FieldType, check_default, test_value as typed
from wholecount.session.survey import survey


def schema_stage(qtbot, qapp, tmp_path, confirm=None):
    return example_window(qtbot, qapp, tmp_path, stage="schema", confirm=confirm)


def test_add_edit_and_remove_a_custom_field(qtbot, qapp, tmp_path):
    w, s = schema_stage(qtbot, qapp, tmp_path)
    body = w.stage_widget
    assert body.add_button.hold.text == "Held until the field has a name."
    body.new_name.setText("Notes Code")
    assert body.add_problem.text() == "Use letters, numbers and underscores, and start with a letter."
    body.new_name.setText("First_Name")
    assert body.add_problem.text() == "A field with this name already exists."
    body.new_name.setText("Notes_Code")
    body.new_type.setCurrentIndex(body.new_type.findData(FieldType.WHOLE_NUMBER))
    body.new_default.setText("abc")
    assert body.add_problem.text() == "The default is not a whole number."
    body.new_default.setText("7")
    assert not body.add_button.held
    body.add_button.button.click()
    settle(qapp)
    assert isinstance(last(s), C.SetupChange) and last(s).section == "schema"
    f = s.schema().get("Notes_Code")
    assert f.type == FieldType.WHOLE_NUMBER and f.default == "7"
    name = w.stage_widget.findChild(QLineEdit, "custom_name_Notes_Code")
    name.setText("Notes_Num")
    name.editingFinished.emit()
    settle(qapp)
    assert s.schema().has("Notes_Num") and not s.schema().has("Notes_Code")
    w.stage_widget.findChild(QPushButton, "remove_Notes_Num").click()
    settle(qapp)
    assert not s.schema().has("Notes_Num")


@pytest.mark.claim("CL-SCHEMA-REMOVE-01")
def test_removing_a_mapped_field_warns_with_the_table_count(qtbot, qapp, tmp_path):
    c = Confirm(False)
    w, s = schema_stage(qtbot, qapp, tmp_path, confirm=c)
    s.history.execute(C.SetupChange("schema", "schema", s.schema().add_custom("Caseload")))
    s.history.execute(C.SetupChange("mappings", ("example_clinic.csv", 0, "Caseload"), "Program"))
    w.refresh()
    settle(qapp)
    w.stage_widget.findChild(QPushButton, "remove_Caseload").click()
    assert c.asked[-1][1] == ("1 tables match a column to this field. They lose that match.",)
    assert s.schema().has("Caseload")
    sv = survey(s)
    assert sum(1 for wk in sv.works.values() if wk.mapping.column_for("Caseload") is not None) == 1


def test_client_id_required_box_and_reset(qtbot, qapp, tmp_path):
    w, s = schema_stage(qtbot, qapp, tmp_path)
    w.stage_widget.findChild(QCheckBox, "clientIdRequired").setChecked(False)
    settle(qapp)
    assert s.schema().get("Client_ID").required is False
    assert "mappings" in s.stale
    w.stage_widget.findChild(QPushButton, "resetSchema").click()
    settle(qapp)
    assert s.schema().get("Client_ID").required is True


@pytest.mark.claim("CL-SCHEMA-DEFAULT-01")
def test_a_default_must_be_of_the_type():
    assert not check_default(FieldType.WHOLE_NUMBER, "abc") and check_default(FieldType.WHOLE_NUMBER, "12")
    assert not check_default(FieldType.YES_NO, "maybe") and check_default(FieldType.TEXT, "anything")


@pytest.mark.claim("CL-SCHEMA-TYPE-01")
def test_a_value_not_of_the_type_fails_and_names_the_field():
    value, reason = typed(Field("Visits", "Visits", FieldType.WHOLE_NUMBER), "three")
    assert reason == "value_wrong_type" and value == "three"


@pytest.mark.claim("CL-SCHEMA-LENGTH-01")
def test_a_value_longer_than_the_limit_fails_and_is_never_cut():
    value, reason = typed(Field("Code", "Code", FieldType.TEXT, max_length=3), "ABCDE")
    assert reason == "value_too_long" and value == "ABCDE"


@pytest.mark.claim("CL-SCHEMA-REQUIRED-01")
def test_no_name_or_no_id_and_no_dob_goes_to_fix_problems(tmp_path):
    from tests.fixtures.session import r_fixture
    from tests.support.m11 import write_csv
    from wholecount.engine.geo.backend import NoBackend
    from wholecount.session.runner import process

    p = write_csv(tmp_path / "t.csv", ["First Name", "Last Name", "Client ID", "DOB", "Zip"],
                  [["Ana", "Lee", "1", "01/02/1980", "11201"], ["", "", "2", "01/02/1980", "11201"],
                   ["Bo", "Roe", "", "", "11201"]])
    s = r_fixture.session(tmp_path / "w", backend=NoBackend(), paths=[p])
    r = process(s)
    by = {row.value("First_Name") or row.value("Client_ID") or "x": r.outcomes[k] for k, row in r.rows.items()}
    assert by["Ana"].counted
    assert not by["2"].counted and by["2"].count_status.value == "not_counted_yet"
    assert not by["Bo"].counted and by["Bo"].count_status.value == "not_counted_yet"
    city = [row for row in r.rows.values() if row.value("First_Name") == "Ana"][0]
    assert city.value("City")           # filled from the ZIP


def test_test_fit_by_source_and_no_tables(qtbot, qapp, tmp_path):
    w, s = schema_stage(qtbot, qapp, tmp_path)
    lines = [x.text() for x in w.stage_widget.fit_card.findChildren(QLabel) if "fields have a column" in x.text()]
    assert len(lines) == len(survey(s).works)


# Tidy up

def prepare_stage(qtbot, qapp, tmp_path):
    return example_window(qtbot, qapp, tmp_path, stage="prepare")


def fill(w, rule, **values):
    body = w.stage_widget
    body.pick_rule(rule)
    for k, v in values.items():
        body._set(k, v, redraw=k == "source")
    return body


@pytest.mark.parametrize("rule,values,expected", [
    ("clean", {"columns": ["Name_first"], "case": "upper", "strip_junk": True},
     {"columns": ["Name_first"], "case": "upper", "strip_junk": True, "strip_edge_punctuation": False}),
    ("split_delim", {"column": "Name_first", "delimiter": "custom", "custom": "/", "maxsplit": 2, "names_text": "a, b"},
     {"column": "Name_first", "delimiter": "comma", "custom": "/", "maxsplit": 2, "names": ["a", "b"]}),
    ("split_address", {"column": "Full_Address"}, {"column": "Full_Address"}),
    ("split_name", {"column": "Name_first", "form": "last_first"}, {"column": "Name_first", "form": "last_first"}),
    ("calc_zip", {"street_col": "Full_Address", "mode": "all", "name": "Zip_calc"},
     {"street_col": "Full_Address", "mode": "all", "name": "Zip_calc"}),
])
def test_each_form_adds_its_step(qtbot, qapp, tmp_path, rule, values, expected):
    w, s = prepare_stage(qtbot, qapp, tmp_path)
    key = next(k for k, wk in survey(s).works.items() if wk.file_name == "example_clinic.csv")
    body = fill(w, rule, source=key, **values)
    assert not body.add_button.held
    body.add_button.button.click()
    settle(qapp)
    cmd = last(s)
    assert cmd.section == "steps" and cmd.key == ("example_clinic.csv", 0)
    step = cmd.new[-1]
    assert step.kind == rule and step.origin == "added" and step.params == expected


def test_add_this_step_names_each_missing_piece(qtbot, qapp, tmp_path):
    w, s = prepare_stage(qtbot, qapp, tmp_path)
    body = fill(w, "clean")
    assert [h.copy_id for h in body.add_button._holds] == ["tidy.hold.source", "tidy.hold.columns"]
    key = next(iter(survey(s).works))
    body = fill(w, "split_delim", source=key, delimiter="custom")
    assert [h.copy_id for h in body.add_button._holds] == ["tidy.hold.column", "tidy.hold.custom"]


@pytest.mark.claim("CL-TIDY-REMOVED-01")
def test_remove_and_restore_round_trip_and_a_removed_step_never_runs(qtbot, qapp, tmp_path):
    from wholecount.session.steps_edit import Step

    w, s = prepare_stage(qtbot, qapp, tmp_path)
    s.history.execute(C.SetupChange("steps", ("example_clinic.csv", 0),
                                    [Step("u1", "clean", {"columns": ["Name"], "case": "upper"})]))
    w.refresh()
    settle(qapp)
    w.stage_widget.findChild(QPushButton, "remove_u1").click()
    settle(qapp)
    assert last(s).new[0].removed
    key = next(k for k, wk in survey(s).works.items() if wk.file_name == "example_clinic.csv")
    wk = survey(s).work(key)
    assert "Name_clean" not in wk.prepared.names()
    assert copy.get("tidy.removed") in [x.text() for x in w.stage_widget.findChildren(QLabel)]
    w.stage_widget.findChild(QPushButton, "restore_u1").click()
    settle(qapp)
    assert not last(s).new[0].removed
    assert "Name_clean" in survey(s).work(key).prepared.names()


def test_a_step_that_does_nothing_is_amber_and_says_what_it_missed(qtbot, qapp, tmp_path):
    from wholecount.session.steps_edit import Step

    w, s = prepare_stage(qtbot, qapp, tmp_path)
    s.history.execute(C.SetupChange("steps", ("example_clinic.csv", 0),
                                    [Step("u1", "split_delim", {"column": "Client_ID", "delimiter": "pipe"})]))
    w.refresh()
    settle(qapp)
    texts = [x.text() for x in w.stage_widget.findChildren(QLabel, "stepResult")]
    assert any(t.startswith(copy.get("tidy.amber.split_found_no_delimiter")) and "safe to remove" in t for t in texts)


def test_groupings_keep_run_order(qtbot, qapp, tmp_path):
    from wholecount.session.steps_edit import Step

    w, s = prepare_stage(qtbot, qapp, tmp_path)
    steps = [Step("u1", "clean", {"columns": ["Name"]}), Step("u2", "split_name", {"column": "Name"}),
             Step("u3", "clean", {"columns": ["Full_Address"]})]
    s.history.execute(C.SetupChange("steps", ("example_clinic.csv", 0), steps))
    for g in ("rule", "source", "who"):
        w.stage_widget.group_by(g)
        settle(qapp)
        order = [f.step_id for f in w.stage_widget.findChildren(object) if hasattr(f, "step_id") and isinstance(f.step_id, str)]
        mine = [x for x in order if x in ("u1", "u2", "u3")]
        if g == "rule":
            assert mine == ["u1", "u3", "u2"]
        else:
            assert mine == ["u1", "u2", "u3"]
    assert w.bridge.pref("tidy_group_by") == "who"


@pytest.mark.claim("CL-TIDY-ZIP-01")
def test_calculated_zip_keeps_existing_values_and_notes_every_row():
    from wholecount.engine.prepare import calc_zip

    class Resolver:
        def zip_for(self, street, city):
            return "11201"

    assert calc_zip.calculate("12 Main St", "", "10001", "blanks", Resolver()) == ("10001", "zip_kept")
    z, note = calc_zip.calculate("12 Main St", "", "", "blanks", Resolver())
    assert z == "11201" and note == "zip_found"
    assert calc_zip.calculate("", "", "", "blanks", Resolver()) == ("", "no_street")


def test_the_zip_note_names_the_real_backend(qtbot, qapp, tmp_path):
    w, s = prepare_stage(qtbot, qapp, tmp_path)
    key = next(iter(survey(s).works))
    fill(w, "calc_zip", source=key)
    texts = [x.text() for x in w.stage_widget.findChildren(QLabel)]
    expected = "tidy.zip.backend.geosupport" if s.backend.name == "geosupport" else "tidy.zip.backend.reference"
    assert copy.get(expected) in texts


def test_continue_keeps_the_steps(qtbot, qapp, tmp_path):
    w, s = prepare_stage(qtbot, qapp, tmp_path)
    w.stage_widget.findChild(QPushButton, "continueMap").click()
    settle(qapp)
    assert isinstance(last(s), C.ConfirmStage) and w.current == "map"
    assert w.view.steps_continued
