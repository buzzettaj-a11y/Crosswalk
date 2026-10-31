"""B-16 (Medium): any five-digit string was read as an Excel date. Now it's never converted, only shown."""
import pytest

from tests.support.std import MONTH_FIRST, TODAY, ids, std
from wholecount.engine.standardize.dates import parse_date


@pytest.mark.parametrize("text,suggestion", [("12345", "1933-10-18"), ("99999", "2173-10-13"), ("73051", "2100-01-01"),
                                             ("60000", "2064-04-08"), ("10000", "1927-05-18"), ("32874", "1990-01-01"), ("00000", None)])
def test_B16_five_digits_are_flagged_with_the_date_they_would_be(text, suggestion):
    r = std(Date_of_Birth=text)
    assert "date_excel_number" in ids(r) and r.value("Date_of_Birth") == text
    assert r.values["Date_of_Birth"].suggestions == ((suggestion,) if suggestion else ())


@pytest.mark.parametrize("text", ["32874.0", "19900415"])
def test_B16_other_digit_strings_are_not_readable(text):
    assert parse_date(text, None, MONTH_FIRST, TODAY).reason == "date_not_readable"


def test_B16_a_date_cell_is_accepted_and_a_numeric_general_cell_is_not_converted():
    assert parse_date("1990-01-01", "date", MONTH_FIRST, TODAY).iso == "1990-01-01"
    assert parse_date("32874", "number", MONTH_FIRST, TODAY).iso is None


def test_B16_the_audits_serial_column_is_refused():
    assert [parse_date(v, "number", MONTH_FIRST, TODAY).reason for v in ("32874", "33000")] == ["date_excel_number"] * 2
