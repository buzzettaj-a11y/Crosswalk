"""Process (M12 section 1): holds in order, the pre-run lines, the run panel, cancel and failure, and what the run found."""
import pytest
from PySide6.QtWidgets import QLabel

from tests.fixtures.session import r_fixture
from tests.support.example_session import PLAN, example_session
from tests.support.m11 import last, run_job, window_for, write_csv
from tests.support.write_spy import WriteSpy
from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount import copy
from wholecount.engine.geo.backend import NoBackend
from wholecount.session import commands as C
from wholecount.session.frame import backend_kind
from wholecount.session.runner import process
from wholecount.ui.stages.run.body import pre_run_lines, process_holds

UI = {"reviewer_asked": True}


def confirm_programs(s):
    for g in PLAN["decisions"]["program_groups"]:
        s.history.execute(C.DecideProgramGroup("confirm", tuple(g["names"]), g["label"]))


@pytest.mark.claim("CL-RUN-HOLD-BLOCKER-01")
@pytest.mark.claim("CL-RUN-HOLD-PROGRAMS-01")
def test_process_holds_in_order(tmp_path):
    s = example_session(tmp_path)
    assert process_holds(s)[0].copy_id == "run.hold.programs"
    n = len(process_holds(s)[0].params) and process_holds(s)[0].params["n"]
    from wholecount.session.survey import survey
    assert n == len(survey(s).program_map.unconfirmed)
    s.history.execute(C.SetupChange("mappings", ("example_clinic.csv", 0, "Last_Name"), ""))
    h = process_holds(s)[0]
    assert (h.copy_id, h.params) == ("run.hold.blocker", {"field": "Last_Name", "table": "example_clinic.csv"})
    assert "Last_Name" in {b.field for b in survey(s).blocks}
    s.history.undo()
    confirm_programs(s)
    assert process_holds(s) == []
    for t in survey(s).tables:
        s.history.execute(C.SetupChange("tables", (t.file_name, t.idx, "included"), False))
    assert process_holds(s)[0].copy_id == "src.hold.no_table"


@pytest.mark.claim("CL-RUN-BACKEND-01")
@pytest.mark.claim("CL-RUN-BACKEND-02")
@pytest.mark.claim("CL-RUN-BACKEND-03")
@pytest.mark.claim("CL-RUN-BACKEND-04")
def test_the_backend_line_comes_from_the_backend_and_does_what_it_says(tmp_path):
    from wholecount.engine.geo.reference import ReferenceBackend

    class Geo:
        name, release = "geosupport", "24B"
    assert backend_kind(Geo()) == "geosupport"
    # Practice: the sample file, and the run is practice.
    from wholecount.session.frame import export_settings

    (tmp_path / "p").mkdir()
    (tmp_path / "n").mkdir()
    s = example_session(tmp_path / "p")
    assert backend_kind(s.backend) == "practice" and s.results.practice
    assert pre_run_lines(s, export_settings(s))[2][0] == "run.pre.backend.practice"
    # None: rows are still checked and counted, and nothing is mapped.
    n = example_session(tmp_path / "n", practice=False)
    assert pre_run_lines(n, export_settings(n))[2][0] == "run.pre.backend.none"
    assert backend_kind(n.backend) == "none"
    assert n.results.counts.counted > 0 and n.results.counts.locations.mapped == 0
    # Reference: exact matches only.
    ref = ReferenceBackend.from_text("house_number,street,zip,borough,latitude,longitude\n12,Oak St,11201,Brooklyn,40.69,-73.99\n")
    assert backend_kind(ref) == "reference"
    assert ref.lookup("12", "Oak St", "11201").placed
    assert not ref.lookup("14", "Oak St", "11201").placed


@pytest.mark.claim("CL-RUN-READS-01")
@pytest.mark.claim("CL-RUN-CHECKS-01")
def test_the_run_reads_each_file_once_changes_none_and_sends_problems_to_review(tmp_path, monkeypatch):
    import hashlib

    from wholecount.session.frame import export_settings
    from wholecount.session.survey import survey

    paths = r_fixture.files(tmp_path / "src")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    s = r_fixture.session(tmp_path / "w", paths=paths)
    lines = dict(pre_run_lines(s, export_settings(s)))
    sv = survey(s)
    assert lines["run.pre.reads"] == {"n": sum(t.included for t in sv.tables), "m": 2}
    s._load_cache = None
    with WriteSpy(monkeypatch) as spy:
        r = process(s)
    assert sorted(x for x in spy.reads if x in {str(p) for p in paths}) == sorted(str(p) for p in paths)
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths} == before
    needs = [k for k, o in r.outcomes.items() if o.reasons and o.set_aside_reason is None and not o.counted]
    assert needs and all(r.outcomes[k].count_status.value == "not_counted_yet" for k in needs)


@pytest.mark.claim("CL-RUN-MAPS-01")
@pytest.mark.claim("CL-RUN-MAPS-02")
@pytest.mark.claim("CL-RUN-MAPS-03")
@pytest.mark.claim("CL-RUN-MAPS-04")
@pytest.mark.claim("CL-SMALLCELL-01")
def test_the_map_line_follows_the_download_switches(tmp_path):
    from tests.support.files_run import ack
    from tests.support.geo import fake
    from tests.support.outputs import read, write
    from wholecount.session.frame import export_settings

    s = r_fixture.session(tmp_path / "w", backend=fake())
    process(s)
    ack(s)
    for flags, key in (({}, "run.pre.maps.default"), ({"exact_coordinates": True}, "run.pre.maps.coords"),
                       ({"map_points": True}, "run.pre.maps.points"),
                       ({"exact_coordinates": True, "map_points": True}, "run.pre.maps.both")):
        for k in ("exact_coordinates", "map_points"):
            s.setup.set("export_settings", k, flags.get(k, False))
        assert pre_run_lines(s, export_settings(s))[3][0] == key
        out = tmp_path / key
        write(s, out, **flags)
        clean = read(out / "Final_Clean_Mapped.csv")
        assert ("Latitude" in clean[0]) == bool(flags.get("exact_coordinates"))
        assert (out / "Map_Points.csv").exists() == bool(flags.get("map_points"))
        counts = read(out / "Map_Counts.csv")
        assert all(r["Count"] == copy.get("map.fewer_than", limit=11) or int(r["Count"]) > 10 for r in counts)


@pytest.mark.claim("CL-RUN-NOWRITE-01")
def test_a_run_writes_nothing_and_folds_to_the_finish_line(qtbot, qapp, tmp_path, monkeypatch):
    s = example_session(tmp_path)
    confirm_programs(s)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    with WriteSpy(monkeypatch) as spy:
        run_job(qtbot, qapp, w, lambda: w.start_process())
    assert spy.writes == []
    text = w.stage_widget.findChild(QLabel, "foldedLine").text()
    assert text.startswith("Last run finished in ") and text.endswith("7 steps, nothing written to disk")


@pytest.mark.claim("CL-CANCEL-UNCHANGED-01")
def test_cancel_leaves_everything_and_says_so(qtbot, qapp, tmp_path):
    from tests.support.session import snapshot

    s = example_session(tmp_path)
    confirm_programs(s)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    before = (snapshot(s), len(s.history.stack))
    w.bridge.runner.started_hook = None
    with qtbot.waitSignal(w.bridge.runner.cancelled, timeout=60000):
        w.start_job(F.DemoJob(seconds=2.0))
        qtbot.waitUntil(lambda: w.model is not None and w.model.current >= 0, timeout=10000)
        w.stage_widget.findChild(type(w.stage_widget.cont), "panelCancel").click()
    settle(qapp)
    assert (snapshot(s), len(s.history.stack)) == before
    assert w.stage_widget.findChild(QLabel, "panelCancelled").text() == copy.get("run.cancelled")


@pytest.mark.claim("CL-CANCEL-UNCHANGED-02")
def test_a_failed_run_shows_the_step_and_code_and_changes_nothing(qtbot, qapp, tmp_path):
    from tests.support.session import snapshot

    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    before = snapshot(s)
    with qtbot.waitSignal(w.bridge.runner.failed, timeout=60000):
        w.start_job(F.DemoJob(seconds=0.05, sleep=lambda x: None, raise_in=0, exc=ValueError("Canary Quorvath")))
    settle(qapp)
    assert snapshot(s) == before
    assert w.stage_widget.findChild(QLabel, "errorCode").text().startswith("Error code E-")
    assert all("Quorvath" not in x.text() for x in w.findChildren(QLabel))


@pytest.mark.claim("CL-BALANCE-TABLES-01")
@pytest.mark.claim("CL-BALANCE-LOC-02")
@pytest.mark.claim("CL-BALANCE-BATCH-01")
def test_what_the_run_found_matches_the_balance_and_expected(qtbot, qapp, tmp_path):
    from wholecount.engine.counts import balance_lines

    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="run", ui=UI)
    (_, rows), (_, loc) = balance_lines(s.results.balance)
    assert w.stage_widget.findChild(QLabel, "foundBalance").text() == copy.get(
        "run.found.balance", counted=rows["counted"], not_counted_yet=rows["not_counted_yet"], aside=rows["set_aside"],
        received=rows["received"])
    exp = PLAN.get("counts", {})
    if "received" in exp:
        assert rows["received"] == exp["received"]
    c = s.results.counts
    assert c.counted == rows["counted"] and c.locations.not_mapped == loc["not_mapped"]
    # Not mapped rows are counted: every one of them is in the counted total.
    not_mapped = [k for k, o in s.results.outcomes.items() if o.counted and o.location and o.location.kind != "mapped"]
    assert len(not_mapped) == loc["not_mapped"]
    bal = s.results.balance
    files = sum(o.accounting.non_empty_rows + o.accounting.shared_rows for o in s.results.load.files if o.status == "ok")
    assert bal.total("received") + bal.excluded_rows + bal.non_table_rows + bal.above_header_rows + bal.header_rows == files
    assert w.stage_widget.findChild(QLabel, "foundOutside").text().startswith(
        f"{bal.excluded_rows} rows are in tables you left out")
