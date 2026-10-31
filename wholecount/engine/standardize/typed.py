"""Typed custom fields (P-STD-7), as the old build's normalize_typed_value."""
import re

from wholecount.engine.schema import FieldType
from wholecount.engine.standardize.dates import parse_date

YES = {"y", "yes", "true", "t", "1"}
NO = {"n", "no", "false", "f", "0"}


def standardize_typed(field, text, kind=None, ctx=None, today=None):
    """(value, reason or None). The value is the standard form, or the text as entered when it doesn't fit."""
    t = text.strip()
    if not t:
        return "", ("required_field_blank" if field.required else None)
    value, reason = t, None
    if field.type == FieldType.WHOLE_NUMBER:
        if not re.fullmatch(r"-?[0-9]+", t):
            reason = "value_wrong_type"
    elif field.type == FieldType.DECIMAL:
        d = t.replace(",", "")
        if re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", d):
            value = d
        else:
            reason = "value_wrong_type"
    elif field.type == FieldType.DATE:
        p = parse_date(t, kind, ctx, today, dob=False)
        if p.iso:
            value = p.iso
        else:
            reason = "value_wrong_type"
    elif field.type == FieldType.YES_NO:
        low = t.lower()
        if low in YES:
            value = "Yes"
        elif low in NO:
            value = "No"
        else:
            reason = "value_wrong_type"
    if reason is None and field.max_length is not None and len(value) > field.max_length:
        return t, "value_too_long"
    return (value if reason is None else t), reason


def validate_default(field, text):
    """The reason a default would be refused when it's saved, or None."""
    import datetime as dt

    _, reason = standardize_typed(field, text, today=dt.date(2000, 1, 1))
    return None if reason == "required_field_blank" else reason
