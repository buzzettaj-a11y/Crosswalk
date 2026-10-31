"""Per-source defaults (P-MAP-4). A default fills a blank and never replaces a value the file supplied (H6).
The caller records every use by record key and field for the audit."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDefault:
    table_key: str
    field: str
    value: str


@dataclass(frozen=True)
class DefaultUse:
    value: str
    used: bool


def default_for(defaults, table_key, field):
    for d in defaults:
        if d.table_key == table_key and d.field == field:
            return d.value
    return None


def fill_default(entered, default, is_blank=lambda v: not v.strip()):
    """The value to use. M04 passes the placeholder-aware is_blank."""
    if default is not None and is_blank(entered):
        return DefaultUse(default, True)
    return DefaultUse(entered, False)
