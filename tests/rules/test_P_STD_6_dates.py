"""P-STD-6: date forms beyond the audit cases."""
import pytest

from tests.support.std import MONTH_FIRST, TODAY
from wholecount.engine.standardize.dates import DateContext, excel_serial, parse_date


@pytest.mark.parametrize("text,iso", [("2024-03-15", "2024-03-15"), ("2024/3/5", "2024-03-05"), ("2024.03.15", "2024-03-15"),
                                      ("3/15/2024", "2024-03-15"), ("3-15-2024", "2024-03-15"), ("3.15.2024", "2024-03-15")])
def test_forms(text, iso):
    assert parse_date(text, None, MONTH_FIRST, TODAY).iso == iso


@pytest.mark.parametrize("text,reason", [("2024-02-30", "date_impossible"), ("02/30/2024", "date_impossible"), ("3/15-2024", "date_not_readable"),
                                         ("March 3", "date_not_readable"), ("13/14/2024", "date_impossible")])
def test_failures(text, reason):
    assert parse_date(text, None, MONTH_FIRST, TODAY).reason == reason


def test_serials():
    assert excel_serial(1) == "1900-01-01" and excel_serial(59) == "1900-02-28" and excel_serial(60) is None
    assert excel_serial(61) == "1900-03-01" and excel_serial(0) is None


def test_no_wall_clock_in_standardize():
    import inspect
    from wholecount.engine import standardize
    import pkgutil, importlib
    for m in pkgutil.iter_modules(standardize.__path__):
        src = inspect.getsource(importlib.import_module(f"wholecount.engine.standardize.{m.name}"))
        assert "date.today(" not in src and "datetime.now(" not in src and ".now()" not in src, m.name
