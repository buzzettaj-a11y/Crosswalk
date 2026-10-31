"""A-09 (High): rows outside the included tables vanished from every output while the page said every row was accounted for."""
import pytest

from tests.conftest import ROOT
from tests.support.load import load

pytestmark = pytest.mark.claim("CL-READ-ACCOUNTING-01")
FIXTURE = ROOT / "tests" / "data" / "audit" / "blankline.csv"


def test_A09_blank_line_gives_one_table_with_a_continuation():
    r = load([FIXTURE])
    t = r.tables[0]
    assert len(r.tables) == 1 and [b.continuation for b in t.blocks] == [False, True]
    assert t.included_row_count == 5
    a = r.files[0].accounting
    assert a.included == 5 and a.balanced()


def test_A09_unticked_continuation_is_counted_as_left_out():
    from tests.support.grids import accounting_of, tables_of
    import csv
    rows = list(csv.reader(FIXTURE.read_text().splitlines()))
    t, _, _ = tables_of(rows)
    t[0].blocks[1].included = False
    a = accounting_of(rows, t)
    assert (a.included, a.excluded, a.rows_left_out, a.non_empty_rows) == (2, 3, 3, 6) and a.balanced()
