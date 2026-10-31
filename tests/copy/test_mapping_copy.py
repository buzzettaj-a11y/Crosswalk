"""Every mapping check reason has a sentence, and its parameters match what check_field sends."""
import inspect
import re

from wholecount import copy
from wholecount.engine import mapping
from wholecount.copy.registry import placeholders

PARAMS = {"col_mostly_empty": {"percent"}, "col_low_fill": {"percent"}, "col_city_many_values": {"distinct"},
          "col_name_mostly_one_value": {"percent"}, "col_id_repeats": {"times"}}


def reason_ids():
    return set(re.findall(r'"(col_[a-z0-9_]+)"', inspect.getsource(mapping)))


def test_every_reason_has_copy_with_matching_params():
    keys = {e.key: e for e in copy.all_entries()}
    for r in reason_ids():
        entry = keys[f"mapping.check.{r}"]
        assert placeholders(entry.text) == PARAMS.get(r, set()), r


def test_question_copy_renders_ints():
    assert "1,200" in copy.get("map.date_order_question", month_first=1200, day_first=0, either=3)
