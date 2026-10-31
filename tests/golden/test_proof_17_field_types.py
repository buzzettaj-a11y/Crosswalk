"""Proof workbook sheet 17 (lines 412 to 429). Rows 1 and 3 write dates in different orders, so they are separate tables here
(P-MAP-5): in one column together, the column would be written both ways."""
import pytest

from tests.support.std import TODAY, ids, std
from wholecount.engine.dateorder import collect_evidence, decide
from wholecount.engine.schema import FieldType, default_schema
from wholecount.engine.standardize.dates import date_context

S = (default_schema().add_custom("Enrolled", type=FieldType.DATE).add_custom("Hours", type=FieldType.DECIMAL)
     .add_custom("Active", type=FieldType.YES_NO))

ROWS = [
    ({"Enrolled": "3/15/2024", "Hours": "12.5", "Active": "Y"}, {"Enrolled": "2024-03-15", "Active": "Yes"}, []),
    ({"Enrolled": "2024-03-15", "Hours": "8", "Active": "no"}, {"Enrolled": "2024-03-15", "Active": "No"}, []),
    ({"Enrolled": "15.03.2024", "Hours": "1,200.75", "Active": "true"}, {"Enrolled": "2024-03-15", "Hours": "1200.75"}, []),
    ({"Enrolled": "not a date", "Hours": "8", "Active": "Y"}, {}, ["value_wrong_type"]),
    ({"Enrolled": "2024-03-15", "Hours": "x", "Active": "Y"}, {}, ["value_wrong_type"]),
    ({"Enrolled": "2024-03-15", "Hours": "8", "Active": "maybe"}, {}, ["value_wrong_type"]),
]


@pytest.mark.parametrize("over,want,reasons", ROWS)
def test_sheet_17(over, want, reasons):
    ctx = date_context(decide(collect_evidence([over["Enrolled"]])))
    r = std(schema=S, contexts={"Enrolled": ctx}, **over)
    assert {f: r.value(f) for f in want} == want and ids(r) == reasons
