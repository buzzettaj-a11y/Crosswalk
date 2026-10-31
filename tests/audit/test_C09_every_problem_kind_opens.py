"""C-09: some problem kinds never opened on the old screen, and a blank first name crashed it. Every kind opens a cause in the
tab its flag names."""
import tomllib

import pytest

from tests.conftest import ROOT
from tests.fixtures.session.problem_rows import PROBLEM_IDS, open_row
from wholecount import copy
from wholecount.engine import reasons
from wholecount.engine.copies import CopyGroup
from wholecount.engine.review import causes

TAB = {"holds_count": "counts", "location": "location", "soft": "look"}


def test_mapping_and_file_agree():
    ids = set(tomllib.loads((ROOT / "wholecount" / "copy" / "problems.toml").read_text(encoding="utf-8")))
    assert ids == set(PROBLEM_IDS)


@pytest.mark.parametrize("rid", PROBLEM_IDS)
def test_every_kind_opens_in_its_tab(rid):
    cs = [c for c in causes([open_row(rid)]) if c.cause_id == rid]
    assert len(cs) == 1
    c = cs[0]
    assert c.tab == TAB[reasons.get(rid).flag] and c.count == 1 and c.actions
    if c.kind == "same_id":
        assert copy.get(c.title_key)
    else:
        problems = tomllib.loads((ROOT / "wholecount" / "copy" / "problems.toml").read_text(encoding="utf-8"))
        assert problems[rid]["title"]


def test_copy_groups_and_same_id_land_in_affects_the_counts():
    groups = [CopyGroup("g1", "identical", "P-DUP-1", ("a", "b")), CopyGroup("g2", "possible", "P-DUP-2", ("c", "d"))]
    cs = causes([open_row("same_id_conflict")], groups)
    kinds = {c.cause_id: (c.tab, c.kind) for c in cs}
    assert kinds["copies_identical"] == ("counts", "copies") and kinds["copies_possible"] == ("counts", "copies")
    assert kinds["same_id_conflict"] == ("counts", "same_id")


def test_blank_first_name_opens():
    (c,) = [c for c in causes([open_row("name_missing")]) if c.cause_id == "name_missing"]
    assert c.tab == "counts" and c.field == "First_Name"
