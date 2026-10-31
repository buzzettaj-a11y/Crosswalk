"""The 19,000-row set (SPEC 13.5, 15) on the fake geocoder: the balance holds, two runs agree, Goal 1 sits where the planted
people say it must, and no step reports a negative or missing count. tools/make_large_set.py writes the set; truth.json holds
counts only."""
import json

import pytest

from tests.acceptance import drive
from tools import make_large_set
from wholecount.engine.counts import assert_balance
from wholecount.engine.geo.fake import FakeGeoBackend
from wholecount.session import commands as C
from wholecount.session.survey import survey
from wholecount.ui.jobs.actions import AddFilesJob, ProcessJob

SEED, ROWS, FILES = 20261030, 19000, 15


@pytest.fixture(scope="module")
def large(tmp_path_factory):
    folder = tmp_path_factory.mktemp("large")
    truth = make_large_set.write_set(SEED, ROWS, FILES, folder)
    s = drive.new_session()
    s.backend = FakeGeoBackend(folder / "fake_gazetteer.csv")
    paths = sorted(p for p in folder.iterdir() if p.name not in ("truth.json", "fake_gazetteer.csv"))
    drive.job(s, AddFilesJob(s, paths))
    for t in survey(s).tables:              # the header row each titled file's card suggests
        if t.suggested_header_row and not t.included:
            s.history.execute(C.SetupChange("tables", (t.file_name, t.idx, "header_row"), t.suggested_header_row))
    for p in survey(s).program_map.unconfirmed:
        s.history.execute(C.DecideProgramGroup("confirm", p.members, p.label))
    drive.job(s, ProcessJob(s))
    first = s.results.digest()
    keys = [m for g in s.results.open_groups if g.kind == "identical" for m in g.members]
    s.history.execute(C.KeepOnePerProgram(keys))      # each exact copy inside a file: keep one
    return s, truth, first


def test_the_set_is_what_was_asked_for(large, tmp_path):
    _, truth, _ = large
    assert truth["rows"] == ROWS and truth["files"] == FILES
    assert truth["titled_files"] > 0 and truth["ambiguous_records"] > 0 and truth["identical_copies"] > 0
    again = make_large_set.write_set(SEED, ROWS, FILES, tmp_path)
    assert again == truth
    assert set(json.loads((tmp_path / "truth.json").read_text(encoding="utf-8"))) == set(truth)


def test_every_row_is_accounted_for(large):
    s, truth, _ = large
    c = s.results.counts
    assert_balance(s.results.balance, s.results.outcomes.values())
    assert c.received == truth["rows"]
    assert c.counted + c.not_counted_yet + c.set_aside == c.received
    assert c.set_aside == truth["identical_copies"]


def test_goal_1_sits_between_the_planted_people_and_the_ambiguous_records(large):
    s, truth, _ = large
    g = s.results.counts.goal1
    planted, ambiguous = truth["people_planted"], truth["ambiguous_records"]
    assert g.low <= planted <= g.high <= planted + ambiguous


def test_no_count_is_negative_or_missing(large):
    s, _, _ = large
    c = s.results.counts
    for name in ("received", "counted", "not_counted_yet", "set_aside", "open_pairs", "open_copy_groups"):
        v = getattr(c, name)
        assert isinstance(v, int) and v >= 0, name
    for r in (c.goal1, c.goal2, *c.per_program.values()):
        assert 0 <= r.low <= r.high
    loc = c.locations
    assert loc.mapped + loc.not_mapped == c.counted


def test_process_again_gives_the_same_results(large):
    s, _, first = large
    s2 = drive.new_session()
    s2.backend = s.backend
    for section, values in s.setup.sections.items():
        s2.setup.sections[section] = dict(values)
    for d in s.decisions:
        if d.kind == "program":
            s2.decisions.add([d])
    drive.job(s2, ProcessJob(s2))
    assert s2.results.digest() == first
