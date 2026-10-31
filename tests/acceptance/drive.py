"""Runs the example batch through the session calls and jobs the stages use, by either route of Add your files (SPEC 13.5).

fast_path(folder) does what the Process all files card does: add the files, choose the header row the card asks about, stop at
Programs while a group is open, confirm the groups, then Process. by_stage(folder) makes every call in stage order and
confirms each stage as a person would. Both take every decision from the `decisions` section of EXPECTED.json, with a fixed
clock and a fixed reviewer name, and both end with a download into the folder given.
"""
import datetime as dt
import json
import pathlib
import shutil

from tests.conftest import ROOT
from tests.support.secrets import TEST_SECRET
from wholecount.engine.geo.backend import NoBackend
from wholecount.engine.progress import NullSink
from wholecount.session import commands as C
from wholecount.session.frame import export_settings, sample_backend
from wholecount.session.secret_store import InstallSecret
from wholecount.session.state import Session
from wholecount.session.survey import survey
from wholecount.ui.jobs.actions import AddFilesJob, DownloadJob, ProcessJob

DATA = ROOT / "wholecount" / "sample_data"
PLAN = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))
NAMES = ("example_clinic.csv", "example_housing.xlsx", "example_partner.tsv", "example_portal.json", "example_state.xml")
REVIEWER = "Acceptance Reviewer"
NOW = dt.datetime(2026, 10, 30, 12, 0, 0, tzinfo=dt.timezone.utc)


def fixed_clock():
    return NOW


def copy_inputs(folder, order=NAMES):
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return [pathlib.Path(shutil.copy(DATA / n, folder / n)) for n in order]


def new_session():
    return Session(InstallSecret(TEST_SECRET), (), backend=NoBackend(), clock=fixed_clock, today=lambda: NOW.date(),
                   getuser=lambda: "")


def job(s, j):
    """A job as the window runs it: run on the worker, then apply inside one command."""
    result = j.run(NullSink())
    if getattr(j, "undoable", True):
        s.history.execute(C.JobCommand(j, result))
    else:
        j.apply(s, result)
    return s


def add_files(s, paths, practice):
    if practice:
        s.history.execute(C.UseExampleData(paths, sample_backend()))
    else:
        job(s, AddFilesJob(s, paths))


def choose_header_rows(s):
    for h in PLAN["decisions"]["header_rows"]:
        t = next(t for t in survey(s).tables if t.file_name == h["file"] and t.sheet == h["sheet"])
        s.history.execute(C.SetupChange("tables", (t.file_name, t.idx, "header_row"), h["header_row"]))


def decide_programs(s):
    for g in PLAN["decisions"]["program_groups"]:
        s.history.execute(C.DecideProgramGroup(g["decision"], tuple(g["names"]), g["label"]))


def _key(s, ref):
    name, row = ref
    r = s.results
    return next(k for k, row_ in r.rows.items() if r.file_of_record[k] == name and row_.row_number == row)


def _group(s, rows):
    members = {_key(s, x) for x in rows}
    return next(g for g in s.results.groups if set(g.members) == members)


def review(s):
    """Fix problems: the reviewer's name first, then copies, same-ID conflicts and pairs. The plan leaves the rows with no
    identifier or no name open (not counted yet), so Finish review stays held, and Download doesn't need it."""
    s.history.execute(C.SetReviewer(REVIEWER))
    d = PLAN["decisions"]
    for g in d["copy_groups"]:
        s.history.execute(C.KeepOneInCopyGroup(_group(s, g["rows"]).group_id, _key(s, g["keep"])))
    for g in d["same_id_conflicts"]:
        s.history.execute(C.DecideSameIdConflict(_group(s, g["rows"]).group_id, g["decision"]))
    for p in d["pairs"]:
        a, b = (s.results.person_of_record[_key(s, x)] for x in p["rows"])
        s.history.execute(C.DecidePair(a, b, {"same_person": "same", "different_people": "different"}[p["decision"]]))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())


def review_open(s):
    """Fix problems with every pair and copy group left open: only the reviewer's name and the low-confidence note."""
    s.history.execute(C.SetReviewer(REVIEWER))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())


def review_different(s):
    """Every possible copy group marked not copies, every same-ID conflict and every open pair decided as different people.
    An identical copy group can't be called not copies (P-DUP), so it keeps one, as the plan says."""
    s.history.execute(C.SetReviewer(REVIEWER))
    kinds = {tuple(map(tuple, g["rows"])): g["kind"] for g in PLAN["people"]["copy_groups"]}
    for g in PLAN["decisions"]["copy_groups"]:
        gid = _group(s, g["rows"]).group_id
        if kinds[tuple(map(tuple, g["rows"]))] == "identical":
            s.history.execute(C.KeepOneInCopyGroup(gid, _key(s, g["keep"])))
        else:
            s.history.execute(C.MarkNotCopies(gid))
    for g in PLAN["decisions"]["same_id_conflicts"]:
        s.history.execute(C.DecideSameIdConflict(_group(s, g["rows"]).group_id, "different_people"))
    for p in list(s.results.identity.proposals):
        s.history.execute(C.DecidePair(*p.pair, "different"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())


def download(s, out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    got = []
    job(s, DownloadJob(s, out, export_settings(s), lambda kind, value: got.append((kind, value))))
    kind, receipt = got[0]
    assert kind == "done", receipt
    return receipt


def fast_path(inputs, out, practice=True, review=review):
    """Add your files' fast path. Returns (session, receipt). review is how Fix problems is answered."""
    s = new_session()
    add_files(s, inputs, practice)
    choose_header_rows(s)
    sv = survey(s)
    if sv.program_map is not None and sv.program_map.unconfirmed:
        decide_programs(s)                     # stopped at Programs; the groups are confirmed there
    job(s, ProcessJob(s))
    review(s)
    return s, download(s, out)


def by_stage(inputs, out, practice=True):
    """Every stage in order, each confirmed as a person would. Returns (session, receipt)."""
    s = new_session()
    add_files(s, inputs, practice)               # 01 Add your files
    choose_header_rows(s)
    survey(s)                                    # 02 Your columns: the schema as it stands
    s.history.execute(C.ConfirmStage("prepare"))  # 03 Tidy up: the proposed steps are kept
    sv = survey(s)                               # 04 Match your columns: each included table confirmed
    for k in sv.works:
        s.history.execute(C.ConfirmTable(sv.table(k).name))
    decide_programs(s)                           # 05 Programs
    job(s, ProcessJob(s))                        # 06 Process
    review(s)                                    # 07 Fix problems
    return s, download(s, out)                   # 08 Results, 09 Download
