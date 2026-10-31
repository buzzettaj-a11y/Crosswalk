"""What Your columns needs from the engine's schema, through the session layer (SPEC 3.2, 4.1)."""
from wholecount.engine.schema import Field, FieldType, SchemaError, default_schema  # noqa: F401
from wholecount.engine.standardize.typed import standardize_typed, validate_default


def check_default(field_type, text):
    """True when a default is a value of the field's type (P-STD-7, the typed-value rule)."""
    return validate_default(Field("x", "x", field_type), text) is None


def test_value(field, text):
    """(value, reason): the engine's typed check, for the claim tests on How a row is tested."""
    return standardize_typed(field, text)
