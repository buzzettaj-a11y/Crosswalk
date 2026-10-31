"""C-23 (Medium): rows in a table the tool left out were invisible to the balance, which couldn't fail."""
import pytest

from tests.support.files import write_text
from tests.support.load import load

pytestmark = pytest.mark.claim("CL-READ-ACCOUNTING-01")

RAW = ("Client_ID,First_Name,Last_Name,DOB,Address,City,State,Zip,Program\n"
       "A1,Ada,Lee,1980-01-01,10 Oak St,Brooklyn,NY,11201,Housing\n"
       "\n"
       ",,,,,,,,\n"
       "A2,Ben,Cho,1981-02-02,11 Oak St,Brooklyn,NY,11201,Housing\n"
       "A3,Cy,Roe,1982-03-03,12 Oak St,Brooklyn,NY,11201,Housing\n")


def test_C23_all_three_rows_included_by_default(tmp_path):
    r = load([write_text(tmp_path, "b.csv", RAW)])
    t = r.tables[0]
    assert len(t.rows) == 3 and t.included_row_count == 3 and r.files[0].accounting.balanced()


def test_C23_unticked_continuation_still_balances(tmp_path):
    from tests.support.grids import accounting_of, tables_of
    import csv
    rows = list(csv.reader(RAW.splitlines()))
    t, _, _ = tables_of([r for r in rows])
    t[0].blocks[1].included = False
    a = accounting_of(rows, t)
    assert len(t[0].rows) == 3
    assert (a.included, a.excluded, a.rows_left_out) == (1, 2, 2) and a.balanced()
