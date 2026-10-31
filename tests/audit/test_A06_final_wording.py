"""A-06: the old Results called counts final while rows were still open. final needs no open pair, copy group or row."""
import csv

import pytest

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from tests.support.session import group
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.runner import process

pytestmark = [pytest.mark.claim("CL-COUNT-02"), pytest.mark.claim("CL-COUNT-03")]


def run(tmp_path, extra=()):
    rows = list(csv.reader((ROOT / "docs" / "audit" / "A-fixtures" / "household.csv").open(encoding="utf-8")))
    rows += [["H400", "", "Quill", "8 Gumdrop Ln", "Brooklyn", "NY", "11201", "Elder Care"]] + list(extra)
    path = tmp_path / "household.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    s = r_fixture.session(tmp_path, paths=[path])
    process(s)
    return s


def h400(s):
    return next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "H400")


def test_one_row_open_then_final(tmp_path):
    s = run(tmp_path)
    s.history.execute(C.DecideSameIdConflict(group(s, "same_id_different").group_id, "different_people"))
    c = s.counts()
    assert not c.final and c.not_counted_yet == 1 and c.open_pairs == 0 and c.open_copy_groups == 0
    assert copy.get("counts.not_final.rows_not_counted_yet", count=c.not_counted_yet).startswith("Settled for the rows counted")
    s.history.execute(C.SetAsideRows([h400(s)], "test_record"))
    c = s.counts()
    zed = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "H300")
    assert s.results.outcomes[zed].counted and s.results.outcomes[zed].location.reason == "address_problem"
    assert c.final and copy.get("counts.final")


def test_not_final_with_a_pair_open(tmp_path):
    s = run(tmp_path)
    s.history.execute(C.DecideSameIdConflict(group(s, "same_id_different").group_id, "approved_as_entered"))
    s.history.execute(C.SetAsideRows([h400(s)], "test_record"))
    c = s.counts()
    assert c.open_pairs == 1 and not c.final


def test_not_final_with_a_copy_group_open(tmp_path):
    s = run(tmp_path, [["H201", "Ada", "Lovelace", "10 Analytical Way", "Queens", "NY", "11101", "Workforce"]])
    s.history.execute(C.DecideSameIdConflict(group(s, "same_id_different").group_id, "different_people"))
    s.history.execute(C.SetAsideRows([h400(s)], "test_record"))
    c = s.counts()
    assert c.open_copy_groups == 1 and not c.final and c.open_pairs == 0
