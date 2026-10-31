"""P-STD-7: typed custom fields, and refusing a bad default."""
import pytest

from tests.support.std import TODAY, ids, std
from wholecount.engine.schema import FieldType, default_schema
from wholecount.engine.standardize.typed import standardize_typed, validate_default

S = default_schema()


def field(t, **kw):
    return S.add_custom("X", type=t, **kw).get("X")


@pytest.mark.parametrize("t,text,value,reason", [
    (FieldType.WHOLE_NUMBER, "12", "12", None), (FieldType.WHOLE_NUMBER, "1.5", "1.5", "value_wrong_type"),
    (FieldType.DECIMAL, "1,200.75", "1200.75", None), (FieldType.DECIMAL, "x", "x", "value_wrong_type"),
    (FieldType.YES_NO, "Y", "Yes", None), (FieldType.YES_NO, "false", "No", None), (FieldType.YES_NO, "maybe", "maybe", "value_wrong_type"),
    (FieldType.DATE, "2024-03-15", "2024-03-15", None), (FieldType.DATE, "not a date", "not a date", "value_wrong_type"),
    (FieldType.TEXT, "anything", "anything", None),
])
def test_types(t, text, value, reason):
    assert standardize_typed(field(t), text, today=TODAY) == (value, reason)


def test_length_and_required():
    assert standardize_typed(field(FieldType.TEXT, max_length=3), "abcd", today=TODAY) == ("abcd", "value_too_long")
    assert standardize_typed(field(FieldType.TEXT, required=True), "", today=TODAY) == ("", "required_field_blank")


def test_validate_default():
    assert validate_default(field(FieldType.WHOLE_NUMBER), "x") == "value_wrong_type"
    assert validate_default(field(FieldType.WHOLE_NUMBER), "3") is None


def test_in_a_row():
    s = S.add_custom("Active", type=FieldType.YES_NO)
    r = std(schema=s, Active="y")
    assert r.value("Active") == "Yes" and "value_standardized" in [n.reason_id for n in r.notes]
    assert ids(std(schema=s, Active="maybe")) == ["value_wrong_type"]
