"""P-VAL-4: summary rows are set aside only when they hold no other person data."""
import pytest

from tests.support.std import std
from wholecount.engine.standardize.model import UnmappedHint

BLANK = dict(First_Name="", Last_Name="", Client_ID="", Address_1="", City="", State="", Zip="", Program="", Address_2="")


@pytest.mark.parametrize("word", ["Total", "Subtotal", "Sub-total", "Grand Total", "Count", "Average", "Avg", "Mean", "Summary", "n = 40",
                                  "All clients"])
def test_summary_words_in_a_name_cell(word):
    assert std(**{**BLANK, "First_Name": word}).set_aside_reason == "summary_row"


def test_with_other_person_data_it_is_a_person():
    assert std(First_Name="Total", Last_Name="Lee").set_aside_reason is None
    assert std(**{**BLANK, "Last_Name": "Total", "Client_ID": "C1"}).set_aside_reason is None


def test_total_in_the_id_column_with_a_count_in_program():
    assert std(**{**BLANK, "Client_ID": "Total", "Program": "65"}).set_aside_reason == "summary_row"


def test_unmapped_hints():
    assert std(**BLANK, unmapped=UnmappedHint(summary_word=True)).set_aside_reason == "summary_row"
    assert std(**BLANK, unmapped=UnmappedHint()).set_aside_reason is None


def test_values_untouched_and_no_reasons():
    r = std(**{**BLANK, "Last_Name": "TOTAL"})
    assert r.value("Last_Name") == "TOTAL" and r.reasons == () and r.notes == ()
