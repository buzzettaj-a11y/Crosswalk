"""The five example files in a session with the planned decisions from EXPECTED.json (M09)."""
import json
import shutil

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from wholecount.engine.geo.backend import NoBackend
from wholecount.engine.geo.reference import ReferenceBackend
from wholecount.session import commands as C
from wholecount.session.runner import process

DATA = ROOT / "wholecount" / "sample_data"
PLAN = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))
NAMES = ["example_clinic.csv", "example_housing.xlsx", "example_partner.tsv", "example_portal.json", "example_state.xml"]


def example_session(tmp_path, practice=True):
    paths = [shutil.copy(DATA / n, tmp_path / n) for n in NAMES]
    backend = ReferenceBackend.from_path(DATA / "sample_reference.csv") if practice else NoBackend()
    s = r_fixture.session(tmp_path, backend=backend, paths=paths, allow_sample=practice)
    for h in PLAN["decisions"]["header_rows"]:
        s.setup.set("tables", (h["file"], 0, "header_row"), h["header_row"])
    process(s)
    return s


def key(s, ref):
    name, row = ref
    return next(k for k, r in s.results.rows.items() if s.results.file_of_record[k] == name and r.row_number == row)


def decide(s):
    d = PLAN["decisions"]
    for g in d["copy_groups"]:
        members = {key(s, x) for x in g["rows"]}
        grp = next(x for x in s.results.groups if set(x.members) == members)
        s.history.execute(C.KeepOneInCopyGroup(grp.group_id, key(s, g["keep"])))
    for g in d["same_id_conflicts"]:
        members = {key(s, x) for x in g["rows"]}
        grp = next(x for x in s.results.groups if set(x.members) == members)
        s.history.execute(C.DecideSameIdConflict(grp.group_id, "different_people"))
    for g in d["program_groups"]:
        s.history.execute(C.DecideProgramGroup("confirm", tuple(g["names"]), g["label"]))
    for p in d["pairs"]:
        a, b = (s.results.person_of_record[key(s, x)] for x in p["rows"])
        s.history.execute(C.DecidePair(a, b, "same"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    return s
