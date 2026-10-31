"""C-18: the old app showed counts from before a set-up change. Results are marked out of date at once, and undo clears it."""
import pytest

from tests.support.session import decided
from wholecount.engine.dateorder import DateFieldSetting, DateOrder
from wholecount.session import commands as C
from wholecount.session.staleness import NODES, StaleResults, downstream


def changes(tmp_path, s):
    s_path = str(tmp_path / "S.csv")
    return [
        (C.SetupChange("sources", s_path, False), "sources"),
        (C.SetupChange("mappings", ("R.csv", 0, "Last_Name"), "Address_1"), "mappings"),
        (C.SetupChange("tables", ("R.csv", 0, "header_row"), 2), "tables"),
        (C.SetupChange("program_columns", ("R.csv", 0), "none"), "programs"),
        (C.SetupChange("date_orders", ("R.csv", 0, "Date_of_Birth"), DateFieldSetting(DateOrder.DAY_FIRST, None)), "standardized"),
        (C.SetupChange("defaults", ("S.csv", 0, "Program"), "Youth"), "standardized"),
        (C.SetupChange("schema", "schema", s.schema().add_custom("Score")), "mappings"),
        (C.SetupChange("run_settings", "extra_fields", frozenset({"census_tract"})), "geo"),
    ]


@pytest.mark.claim("CL-COUNT-06")
@pytest.mark.parametrize("i", range(8))
def test_stale_until_undo(tmp_path, i):
    s = decided(tmp_path)
    cmd, node = changes(tmp_path, s)[i]
    digest = s.results.digest()
    s.history.execute(cmd)
    assert s.stale_nodes == downstream(node) and s.stale == downstream(node) - {"exports"}
    assert set(cmd.invalidates) >= s.stale_nodes
    with pytest.raises(StaleResults):
        s.counts()
    assert s.download_gate().reasons == ("stale",)
    s.history.undo()
    assert s.stale == frozenset() and s.results.digest() == digest
    s.counts()


def test_nodes_in_order():
    assert NODES[0] == "sources" and NODES[-1] == "exports" and NODES.index("decisions") < NODES.index("identity")
