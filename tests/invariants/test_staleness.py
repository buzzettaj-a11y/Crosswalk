"""STALE-2: every set-up change declares at least the nodes its fingerprints make stale, for every section."""
import pytest

from tests.support.session import base
from wholecount.session import commands as C
from wholecount.session.state import SECTIONS

VALUES = {"sources": ("x.csv", True), "tables": (("R.csv", 0, "included"), False), "steps": (("R.csv", 0), ()),
          "mappings": (("R.csv", 0, "Program"), ""), "defaults": (("R.csv", 0, "Program"), "Youth"),
          "date_orders": (("R.csv", 0, "Date_of_Birth"), None), "program_columns": (("R.csv", 0), "none"),
          "run_settings": ("extra_fields", frozenset({"census_tract"})), "export_settings": ("x", 1)}


@pytest.mark.parametrize("section", [s for s in SECTIONS if s != "schema"])
def test_declared_covers_actual(tmp_path, section):
    s = base(tmp_path)
    key, value = VALUES[section]
    cmd = C.SetupChange(section, key, value)
    s.history.execute(cmd)
    assert s.stale and cmd.invalidates >= s.stale
    s.history.undo()
    assert not s.stale


def test_decisions_declare_what_they_touch(tmp_path):
    s = base(tmp_path)
    p = s.results.identity.proposals[0]
    for cmd in (C.SendToRowByRow("name_missing"), C.DecidePair(*p.pair, "different"), C.DecideProgramGroup("confirm", ("Housing", "Youth"))):
        before = s.live_fingerprints()
        s.history.execute(cmd)
        after = s.live_fingerprints()
        assert {n for n in before if before[n] != after[n]} <= cmd.invalidates
