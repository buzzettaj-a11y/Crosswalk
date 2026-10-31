"""The fields every table maps onto (SPEC 4.1). The schema is set-up, never client data."""
import enum
import re
from dataclasses import asdict, dataclass, replace

_CUSTOM_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")


class FieldType(enum.Enum):
    TEXT = "text"
    WHOLE_NUMBER = "whole_number"
    DECIMAL = "decimal"
    DATE = "date"
    YES_NO = "yes_no"


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: FieldType = FieldType.TEXT
    required: bool = False                # a column must exist, or Process is blocked
    required_for_mapping: bool = False    # needed to place the address, never to count
    needed_to_count: bool = False         # a custom field the count rule checks (M04)
    default: str | None = None
    max_length: int | None = None
    builtin: bool = False
    enabled: bool = True


ADDRESS_FIELDS = ("Address_1", "Address_2", "City", "State", "Zip")
NAME_FIELDS = ("First_Name", "Middle_Initial", "Last_Name")


def _builtin(key, label, **kw):
    return Field(key, label, builtin=True, **kw)


DEFAULT_FIELDS = (
    _builtin("First_Name", "First Name", required=True, max_length=60),
    _builtin("Middle_Initial", "Middle Initial", max_length=1),
    _builtin("Last_Name", "Last Name", required=True, max_length=60),
    _builtin("Client_ID", "Client ID", required=True, max_length=30),
    _builtin("Address_1", "Address 1", required_for_mapping=True, max_length=150),
    _builtin("Address_2", "Address 2", max_length=150),
    _builtin("City", "City", required_for_mapping=True, max_length=50),
    _builtin("State", "State", required_for_mapping=True, max_length=2),
    _builtin("Zip", "Zip", required_for_mapping=True, max_length=5),
    _builtin("Program", "Program", max_length=80),
    _builtin("Date_of_Birth", "Date of Birth", type=FieldType.DATE),
)
BUILTIN_KEYS = tuple(f.key for f in DEFAULT_FIELDS)


class SchemaError(ValueError):
    """A change the schema doesn't allow. Carries a reason ID."""


@dataclass(frozen=True)
class Schema:
    fields: tuple

    def get(self, key):
        for f in self.fields:
            if f.key == key:
                return f
        raise KeyError(key)

    def has(self, key):
        return any(f.key == key for f in self.fields)

    def enabled_fields(self):
        return tuple(f for f in self.fields if f.enabled)

    def is_enabled(self, key):
        return self.has(key) and self.get(key).enabled

    def _swap(self, field):
        return Schema(tuple(field if f.key == field.key else f for f in self.fields))

    def with_required(self, key, required):
        """Client_ID may be made optional for the batch. That removes only the column requirement (SPEC 4.1)."""
        f = self.get(key)
        if f.builtin and key != "Client_ID":
            raise SchemaError("builtin_fixed")
        return self._swap(replace(f, required=required))

    def with_enabled(self, key, enabled):
        f = self.get(key)
        if f.builtin and key != "Date_of_Birth":
            raise SchemaError("builtin_fixed")
        return self._swap(replace(f, enabled=enabled))

    def add_custom(self, key, type=FieldType.TEXT, default=None, max_length=None, required=False, needed_to_count=False, label=None):
        if not isinstance(key, str) or not _CUSTOM_KEY.fullmatch(key):
            raise SchemaError("custom_key_invalid")
        if any(f.key.lower() == key.lower() for f in self.fields):
            raise SchemaError("custom_key_taken")
        if not isinstance(type, FieldType):
            raise SchemaError("custom_type_invalid")
        if max_length is not None and (isinstance(max_length, bool) or not isinstance(max_length, int) or not 1 <= max_length <= 1000):
            raise SchemaError("custom_max_length_invalid")
        if default is not None and not isinstance(default, str):
            raise SchemaError("custom_default_not_text")
        f = Field(key, label or key.replace("_", " "), type, required=required, needed_to_count=needed_to_count, default=default,
                  max_length=max_length)
        return Schema(self.fields + (f,))

    def remove_custom(self, key):
        if self.get(key).builtin:
            raise SchemaError("builtin_fixed")
        return Schema(tuple(f for f in self.fields if f.key != key))

    def to_dict(self):
        return {"fields": [dict(asdict(f), type=f.type.value) for f in self.fields]}

    @classmethod
    def from_dict(cls, data):
        return cls(tuple(Field(**dict(d, type=FieldType(d["type"]))) for d in data["fields"]))


def default_schema():
    return Schema(DEFAULT_FIELDS)
