"""Each factual help sentence (M15) is true of the code. Every test drives the behavior, not the string."""
import hashlib

import pytest

from tests.support.example_session import decide, example_session


@pytest.fixture
def s(tmp_path):
    return example_session(tmp_path)


@pytest.mark.claim("CL-HELP-RUN-01")
def test_process_changes_no_file_and_problem_rows_wait(tmp_path):
    from tests.support.example_session import DATA, NAMES
    before = {n: hashlib.sha256((DATA / n).read_bytes()).hexdigest() for n in NAMES}
    s = example_session(tmp_path)
    after = {n: hashlib.sha256((tmp_path / n).read_bytes()).hexdigest() for n in NAMES}
    assert before == after
    waiting = [o for o in s.results.outcomes.values() if o.reasons and o.set_aside_reason is None and not o.counted]
    assert waiting and all(o.count_status.value == "not_counted_yet" for o in waiting)


@pytest.mark.claim("CL-HELP-REVIEW-01")
def test_finish_is_held_by_counts_causes_and_the_name_is_saved(s):
    from wholecount.session import commands as C
    from wholecount.session.pages import cause_views, gate

    assert gate(s).held
    c = next(v.cause for v in cause_views(s) if v.cause.cause_id == "name_missing")
    s.reviewer = "Avery"
    s.history.execute(C.SetAsideRows(c.record_keys, "test_record"))
    assert all(d.reviewer == "Avery" for d in s.decisions if d.kind == "set_aside")


@pytest.mark.claim("CL-HELP-RESULTS-01")
@pytest.mark.claim("CL-HELP-PAIRS-01")
def test_a_range_until_every_pair_is_decided(s):
    c = s.results.counts
    assert c.open_pairs and c.goal1.low < c.goal1.high
    assert s.results.identity.proposals and not [j for j in s.results.identity.auto_joins
                                                 if set(j.pair) == set(s.results.identity.proposals[0].pair)]
    decide(s)
    c = s.results.counts
    assert c.open_pairs == 0 and c.goal1.low == c.goal1.high


@pytest.mark.claim("CL-HELP-EXPORT-01")
def test_practice_writes_no_maps_and_formats(tmp_path, monkeypatch):
    from tests.support.outputs import write
    from tests.support.write_spy import WriteSpy

    from wholecount.session.runner import process

    s = example_session(tmp_path)
    with WriteSpy(monkeypatch) as spy:      # processing and deciding write nothing; only Download does
        process(s)
        decide(s)
    assert spy.writes == []
    write(s, tmp_path / "out", formats={"Unique_Clients": "xlsx", "Final_Clean_Mapped": "json"})
    names = {p.name for p in (tmp_path / "out").iterdir()}
    assert not [n for n in names if "Map_" in n]
    assert "PRACTICE_Unique_Clients.xlsx" in names and "PRACTICE_Final_Clean_Mapped.json" in names


@pytest.mark.claim("CL-HELP-CONF-01")
def test_low_holds_download_until_ticked(tmp_path):
    from tests.support.session import base
    from wholecount.session import commands as C

    s = base(tmp_path)
    conf = s.results.confidence
    assert conf.level == "low" and {p[0] for p in conf.parts} <= {"counted_short", "pairs_open", "placed_short"}
    assert "low_confidence_unacked" in s.download_gate().reasons
    s.history.execute(C.AcknowledgeLowConfidence())
    assert "low_confidence_unacked" not in s.download_gate().reasons


@pytest.mark.claim("CL-HELP-PROGRAMS-01")
def test_nothing_is_grouped_until_confirmed(tmp_path):
    from tests.support.example_session import PLAN
    from wholecount.session import commands as C

    s = example_session(tmp_path)
    g = PLAN["decisions"]["program_groups"][0]
    before = set(s.results.program_of_record.values())
    assert len(set(g["names"]) & before) > 1        # still separate names until confirmed
    s.history.execute(C.DecideProgramGroup("confirm", tuple(g["names"]), g["label"]))
    after = set(s.results.program_of_record.values())
    assert not (set(g["names"]) - {g["label"]}) & after and g["label"] in after


@pytest.mark.claim("CL-HELP-MAP-01")
def test_moved_points_and_small_counts(tmp_path):
    from tests.fixtures.outputs.fixture import districts, session
    from tests.fixtures.session import r_fixture
    from tests.support.files_run import run, write_csv
    from tests.support.outputs import read, write
    from wholecount import copy
    from wholecount.engine.geo.offset import haversine_ft

    plain = session(tmp_path / "a")
    write(plain, tmp_path / "plain")
    assert all(r["Count"] == copy.get("map.fewer_than", limit=11) for r in read(tmp_path / "plain" / "Map_Counts.csv"))
    rows = [[f"D{i:04d}", f"Given{i}", f"Family{i}", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"]
            for i in range(30)]
    cols = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
    s = run(tmp_path / "b", [write_csv(tmp_path / "in" / "door.csv", cols, rows)], districts=districts(tmp_path),
            backend=r_fixture.reference())
    write(s, tmp_path / "o", map_points=True)
    pts = read(tmp_path / "o" / "Map_Points.csv")
    assert len({(p["Latitude"], p["Longitude"]) for p in pts}) == 1
    door = r_fixture.GAZETTEER[0]
    assert 149.5 <= haversine_ft(door[4], door[5], float(pts[0]["Latitude"]), float(pts[0]["Longitude"])) <= 250.5


@pytest.mark.claim("CL-HELP-KEYS-01")
def test_keys_follow_contents_not_positions():
    from tests.support.secrets import OTHER_SECRET, TEST_SECRET
    from wholecount.session import keys
    from wholecount.session.secret_store import InstallSecret

    tk = "t :: data :: 00000000"
    rows = [["Ada", "1 A St"], ["Bo", "2 B St"], ["Cy", "3 C St"]]
    a = keys.record_keys(InstallSecret(TEST_SECRET), tk, rows)
    b = keys.record_keys(InstallSecret(TEST_SECRET), tk, list(reversed(rows)))
    assert set(a) == set(b)
    assert set(keys.record_keys(InstallSecret(OTHER_SECRET), tk, rows)) != set(a)


@pytest.mark.claim("CL-HELP-BALANCE-01")
@pytest.mark.claim("CL-HELP-NOTMAPPED-01")
def test_both_balances_and_not_mapped_people_count(s):
    c = s.results.counts
    assert s.results.balance.total("received") == c.counted + c.not_counted_yet + c.set_aside
    loc = c.locations
    assert c.counted == loc.mapped + loc.not_mapped
    nm = [k for k, o in s.results.outcomes.items() if o.counted and o.location and o.location.kind != "mapped"]
    assert nm and all(s.results.identity.master_of_record.get(k) for k in nm)


@pytest.mark.claim("CL-HELP-ASIDE-01")
def test_set_aside_rows_are_kept_and_can_return(tmp_path):
    from tests.support.outputs import read, write
    from wholecount.session import commands as C
    from wholecount.session.pages import cause_views

    s = example_session(tmp_path)
    c = next(v.cause for v in cause_views(s) if v.cause.cause_id == "name_missing")
    keys = list(c.record_keys)
    s.history.execute(C.SetAsideRows(keys, "test_record"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    write(s, tmp_path / "out")
    aside = read(tmp_path / "out" / "PRACTICE_Set_Aside_Records.csv")
    assert set(keys) <= {r["Record_Key"] for r in aside}
    s.history.execute(C.ReturnToOpen(keys))
    assert all(s.results.outcomes[k].set_aside_reason is None for k in keys)


@pytest.mark.claim("CL-HELP-REVIEWER-01")
def test_reviewer_on_logs_and_second_name_over_200(s):
    from wholecount.engine.outputs.audit_text import render_internal, render_shareable
    from wholecount.session.export import build_view
    from wholecount.session.reviewer_view import needs_second

    decide(s)
    view = build_view(s)
    assert s.reviewer in render_internal(view) and s.reviewer in render_shareable(view)
    assert needs_second(201) and not needs_second(200)
