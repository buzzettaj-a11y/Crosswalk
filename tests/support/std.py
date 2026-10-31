"""Standardize one literal row, for M04 tests. The base row is a counted Brooklyn client with every check passing."""
import datetime as dt

from wholecount.engine.dateorder import DateOrder
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.dates import DateContext
from wholecount.engine.standardize.model import AddressText, RowInput, UnmappedHint
from wholecount.engine.standardize.rows import TableOptions, standardize_row

TODAY = dt.date(2026, 10, 30)
BASE = {"First_Name": "Ada", "Middle_Initial": "", "Last_Name": "Sample", "Client_ID": "P001", "Address_1": "209 Joralemon St",
        "Address_2": "", "City": "Brooklyn", "State": "NY", "Zip": "11201", "Program": "Youth", "Date_of_Birth": ""}
MONTH_FIRST = DateContext(DateOrder.MONTH_FIRST, "resolved", False, None)


def row_input(record_key="rk", kinds=None, address_text=AddressText(), unmapped=UnmappedHint(), defaults_used=(), step_reasons=(),
              **values):
    v = dict(BASE)
    v.update(values)
    return RowInput(record_key, "t", 2, v, kinds or {}, address_text, unmapped, tuple(defaults_used), tuple(step_reasons))


def std(schema=None, contexts=None, today=TODAY, approved=False, **kw):
    schema = schema or default_schema()
    return standardize_row(row_input(**kw), schema, TableOptions(contexts or {"Date_of_Birth": MONTH_FIRST}), today)


def ids(row):
    return sorted(set(row.reason_ids()))
