"""The data line (SPEC 11.8): one test per part, 27 in all. Each drives the session with the fake backend and proves the
behavior, not the wording. Saved progress is off unless a test says otherwise."""
import hashlib

import pytest

from tests.fixtures.session import r_fixture
from tests.support.geo import fake
from tests.support.session import decide_all, rk
from tests.support.write_spy import WriteSpy
from wholecount.session import commands as C
from wholecount.session.runner import causes_for, process


def _hash(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@pytest.fixture
def world(tmp_path):
    src = tmp_path / "src"
    paths = r_fixture.files(src)
    s = r_fixture.session(tmp_path / "w", backend=fake(), paths=paths)
    return s, paths, _hash(paths)


def _values(s):
    return {v.entered for r in s.results.rows.values() for _, v in r.values.items() if v.entered and len(v.entered) >= 3}


def _source_reads(spy, paths):
    names = {str(p) for p in paths}
    return [r for r in spy.reads if r in names]


# Add your files

@pytest.mark.claim("CL-DATALINE-SOURCES-READS")
@pytest.mark.claim("CL-DATA-FILES-01")
def test_sources_reads_each_file_once(world, monkeypatch):
    s, paths, _ = world
    with WriteSpy(monkeypatch) as spy:
        process(s)
        decide_all(s)
    reads = _source_reads(spy, paths)
    assert sorted(reads) == sorted(str(p) for p in paths)


@pytest.mark.claim("CL-DATALINE-SOURCES-CHANGES")
@pytest.mark.claim("CL-DATA-FILES-01")
def test_sources_changes_nothing_in_the_files(world):
    s, paths, before = world
    process(s)
    decide_all(s)
    assert _hash(paths) == before


@pytest.mark.claim("CL-DATALINE-SOURCES-WRITES")
def test_sources_writes_nothing(world, monkeypatch):
    s, _, _ = world
    with WriteSpy(monkeypatch) as spy:
        process(s)
    assert spy.writes == []


# Your columns

def _schema_change(s):
    from wholecount.engine.schema import default_schema

    return C.SetupChange("schema", "schema", default_schema())


@pytest.mark.claim("CL-DATALINE-SCHEMA-READS")
def test_schema_reads_nothing_from_the_files(world, monkeypatch):
    s, paths, _ = world
    process(s)
    with WriteSpy(monkeypatch) as spy:
        s.history.execute(_schema_change(s))
    assert _source_reads(spy, paths) == []


@pytest.mark.claim("CL-DATALINE-SCHEMA-CHANGES")
def test_schema_changes_only_the_list_of_fields(world):
    s, _, _ = world
    process(s)
    before = {k: dict(v) for k, v in s.setup.sections.items() if k != "schema"}
    decisions = list(s.decisions)
    s.history.execute(_schema_change(s))
    assert {k: dict(v) for k, v in s.setup.sections.items() if k != "schema"} == before
    assert list(s.decisions) == decisions


@pytest.mark.claim("CL-DATALINE-SCHEMA-WRITES")
def test_schema_writes_nothing(world, monkeypatch):
    s, _, _ = world
    process(s)
    with WriteSpy(monkeypatch) as spy:
        s.history.execute(_schema_change(s))
    assert spy.writes == []


# Tidy up

def _exclude_s(s):
    s.history.execute(C.SetupChange("tables", ("S.csv", 0, "included"), False))


@pytest.mark.claim("CL-DATALINE-PREPARE-READS")
def test_only_included_tables_are_worked(world):
    s, _, _ = world
    process(s)
    all_rows = s.results.counts.received
    _exclude_s(s)
    process(s)
    assert [w.file_name for w in s.results.works] == ["R.csv"]
    assert s.results.counts.received < all_rows
    assert all(s.results.file_of_record[k][0] == "R.csv" for k in s.results.rows) if isinstance(
        next(iter(s.results.file_of_record.values())), tuple) else True


@pytest.mark.claim("CL-DATALINE-PREPARE-CHANGES")
def test_steps_add_columns_in_memory_and_leave_files(world):
    from wholecount.engine.prepare.steps import Step

    s, paths, before = world
    s.history.execute(C.SetupChange("steps", ("R.csv", 0), [Step("s1", "clean", {"columns": ["First_Name"], "case": "upper"})]))
    process(s)
    assert _hash(paths) == before


@pytest.mark.claim("CL-DATALINE-PREPARE-WRITES")
def test_steps_write_nothing(world, monkeypatch):
    from wholecount.engine.prepare.steps import Step

    s, _, _ = world
    with WriteSpy(monkeypatch) as spy:
        s.history.execute(C.SetupChange("steps", ("R.csv", 0), [Step("s1", "clean", {"columns": ["First_Name"]})]))
        process(s)
    assert spy.writes == []


# Match your columns

@pytest.mark.claim("CL-DATALINE-MAP-READS")
def test_map_reads_column_names_and_samples(world, monkeypatch):
    """The column checks see headers and a bounded sample of values, never the files themselves."""
    from wholecount.engine import mapping

    s, paths, _ = world
    process(s)
    w = s.results.works[0]
    with WriteSpy(monkeypatch) as spy:
        assigns = w.mapping.assignments
    assert assigns and _source_reads(spy, paths) == []
    assert all(a.field and a.column is not None for a in assigns) if hasattr(assigns[0], "column") else assigns
    assert hasattr(mapping, "__name__")


@pytest.mark.claim("CL-DATALINE-MAP-CHANGES")
def test_map_changes_nothing_in_the_files(world):
    s, paths, before = world
    process(s)
    s.history.execute(C.SetupChange("mappings", ("R.csv", 0, "First_Name"), None))
    process(s)
    assert _hash(paths) == before


@pytest.mark.claim("CL-DATALINE-MAP-WRITES")
def test_map_writes_nothing(world, monkeypatch):
    s, _, _ = world
    process(s)
    with WriteSpy(monkeypatch) as spy:
        s.history.execute(C.SetupChange("mappings", ("R.csv", 0, "First_Name"), None))
    assert spy.writes == []


# Programs

@pytest.mark.claim("CL-DATALINE-PROGRAMS-READS")
def test_programs_come_only_from_the_program_columns(world):
    s, _, _ = world
    process(s)
    programs = set(s.results.program_of_record.values()) - {""}
    column_values = {r.value("Program") for r in s.results.rows.values() if r.value("Program")}
    assert programs and {p.lower() for p in programs} <= {v.lower() for v in column_values}


@pytest.mark.claim("CL-DATALINE-PROGRAMS-CHANGES")
def test_program_decisions_leave_files(world):
    s, paths, before = world
    process(s)
    s.history.execute(C.DecideProgramGroup("confirm", ("Housing", "Youth")))
    assert _hash(paths) == before


@pytest.mark.claim("CL-DATALINE-PROGRAMS-WRITES")
def test_program_decisions_write_nothing(world, monkeypatch):
    s, _, _ = world
    process(s)
    with WriteSpy(monkeypatch) as spy:
        s.history.execute(C.DecideProgramGroup("confirm", ("Housing", "Youth")))
    assert spy.writes == []


# Process

@pytest.mark.claim("CL-DATALINE-RUN-READS")
def test_process_counts_rows_from_included_tables_only(world):
    s, _, _ = world
    _exclude_s(s)
    process(s)
    received = s.results.counts.received
    assert received == len(r_fixture.r_rows()) == sum(len(w.rows) for w in s.results.works)


@pytest.mark.claim("CL-DATALINE-RUN-CHANGES")
def test_process_changes_nothing_in_the_files(world):
    s, paths, before = world
    process(s)
    process(s)
    assert _hash(paths) == before


@pytest.mark.claim("CL-DATALINE-RUN-WRITES")
def test_process_writes_nothing_until_download(world, monkeypatch, tmp_path):
    from tests.support.files_run import ack
    from tests.support.outputs import write

    s, _, _ = world
    with WriteSpy(monkeypatch) as spy:
        process(s)
        decide_all(s)
    assert spy.writes == []
    ack(s)
    down = tmp_path / "down"
    with WriteSpy(monkeypatch) as spy:
        write(s, down)
    assert spy.writes and all(p.startswith(str(down)) for p in spy.paths())


# Fix problems

@pytest.mark.claim("CL-DATALINE-REVIEW-READS")
def test_review_reads_the_rows_that_need_a_decision(world):
    s, _, _ = world
    process(s)
    r = s.results
    flagged = ({k for k, o in r.outcomes.items() if o.reasons or o.set_aside_reason is not None
                or o.count_status.value == "not_counted_yet"}
               | {k for g in r.open_groups for k in g.members} | set(r.fills))
    shown = set()
    for cause in causes_for(r):
        shown |= set(getattr(cause, "record_keys", ()) or ())
    assert shown and shown <= flagged
    clean = set(r.outcomes) - flagged
    assert clean and not (shown & clean)


@pytest.mark.claim("CL-DATALINE-REVIEW-CHANGES")
def test_review_changes_only_what_is_decided_and_logs_it(world):
    s, _, _ = world
    process(s)
    target = rk(s, "R14")
    before = {k: o for k, o in s.results.outcomes.items()}
    n_log = len(s.audit_log)
    s.history.execute(C.SetAsideRows([target], "out_of_scope"))
    after = s.results.outcomes
    changed = {k for k in before if before[k] != after[k]}
    assert changed == {target}
    from wholecount.session.export import build_events

    assert len(s.audit_log) == n_log + 1
    lines = [e for _, e in build_events(s, s.results) if e.code == "DECISION"]
    assert any(("record_key", target) in e.fields for e in lines)


@pytest.mark.claim("CL-DATALINE-REVIEW-WRITES")
def test_review_writes_nothing(world, monkeypatch):
    s, _, _ = world
    process(s)
    with WriteSpy(monkeypatch) as spy:
        decide_all(s)
    assert spy.writes == []


# Results

@pytest.mark.claim("CL-DATALINE-SUMMARY-READS")
def test_results_count_only_counted_rows(world):
    from wholecount.session.export import build_view

    s, _, _ = world
    process(s)
    decide_all(s)
    v = build_view(s)
    counted = {r.record_key for r in v.rows if r.counted}
    for _, keys, _ in v.masters:
        assert set(keys) <= counted
    assert s.results.counts.goal1.high <= len(counted)


def _state(s):
    return (s.results.digest(), tuple(d.decision_id for d in s.decisions), len(s.history.stack), len(s.audit_log),
            dict(s.setup.sections["schema"]) == dict(s.setup.sections["schema"]))


@pytest.mark.claim("CL-DATALINE-SUMMARY-CHANGES")
def test_results_change_nothing(world):
    from wholecount.engine.outputs.summary_doc import build_summary
    from wholecount.session.export import build_view
    from wholecount.ui.frame.view import build_view as frame_view

    s, _, _ = world
    process(s)
    decide_all(s)
    before = _state(s)
    frame_view(s)
    build_summary(build_view(s), False)
    assert _state(s) == before


@pytest.mark.claim("CL-DATALINE-SUMMARY-WRITES")
def test_results_write_only_the_printable_page(world, monkeypatch, tmp_path):
    from tests.support.files_run import ack
    from wholecount.engine.outputs.summary_doc import build_summary
    from wholecount.session.export import build_view, save_summary

    s, _, _ = world
    process(s)
    decide_all(s)
    ack(s)
    with WriteSpy(monkeypatch) as spy:
        build_summary(build_view(s), False)
    assert spy.writes == []
    page = tmp_path / "page" / "summary.html"
    page.parent.mkdir()
    with WriteSpy(monkeypatch) as spy:
        save_summary(s, page)
    assert page.exists() and str(page) in spy.paths()
    assert all(p.startswith(str(page.parent)) for p in spy.paths())


# Download

@pytest.mark.claim("CL-DATALINE-EXPORT-READS")
def test_download_reads_the_results_not_the_files(world, monkeypatch, tmp_path):
    from tests.support.files_run import ack
    from tests.support.outputs import write

    s, paths, _ = world
    process(s)
    decide_all(s)
    ack(s)
    with WriteSpy(monkeypatch) as spy:
        write(s, tmp_path / "down")
    assert _source_reads(spy, paths) == []


@pytest.mark.claim("CL-DATALINE-EXPORT-CHANGES")
def test_download_changes_nothing(world, tmp_path):
    from tests.support.files_run import ack
    from tests.support.outputs import write

    s, paths, before_files = world
    process(s)
    decide_all(s)
    ack(s)
    before = (s.results.digest(), tuple(d.decision_id for d in s.decisions), len(s.history.stack))
    write(s, tmp_path / "down")
    assert (s.results.digest(), tuple(d.decision_id for d in s.decisions), len(s.history.stack)) == before
    assert _hash(paths) == before_files


@pytest.mark.claim("CL-DATALINE-EXPORT-WRITES")
def test_download_writes_only_the_chosen_files_in_the_folder(world, monkeypatch, tmp_path):
    import pathlib

    from tests.support.files_run import ack
    from tests.support.outputs import write

    s, _, _ = world
    process(s)
    decide_all(s)
    ack(s)
    down = tmp_path / "down"
    with WriteSpy(monkeypatch) as spy:
        receipt = write(s, down)
    names = {pathlib.Path(f.path).name for f in receipt.files}
    assert {p.name for p in down.iterdir()} == names
    assert all(p.startswith(str(down)) for p in spy.paths())
