"""The copy registry: loads en.toml and formats entries (H11, H16)."""
import string
import tomllib
from dataclasses import dataclass
from importlib import resources

from wholecount.brand import PRODUCT_NAME

INJECTED = frozenset({"product"})


@dataclass(frozen=True)
class Entry:
    key: str
    text: str
    claim: str | None = None


class CopyError(KeyError):
    """A missing key, or parameters that don't match the entry's placeholders."""


def _flatten(table, prefix=()):
    for name, value in table.items():
        if not isinstance(value, dict):
            continue
        path = prefix + (name,)
        if "text" in value:
            yield Entry(".".join(path), value["text"], value.get("claim"))
        else:
            yield from _flatten(value, path)


def load(toml_text):
    """Entries from TOML text, keyed by dotted key. Tests use this on a temp registry."""
    return {e.key: e for e in _flatten(tomllib.loads(toml_text))}


_ENTRIES = None


def _entries():
    global _ENTRIES
    if _ENTRIES is None:
        _ENTRIES = load(resources.files("wholecount.copy").joinpath("en.toml").read_text(encoding="utf-8"))
    return _ENTRIES


def placeholders(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f is not None}


def _format_value(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}"
    return v


def render(entry, params):
    """Format an entry. Raises CopyError for a missing parameter, an unused one, or a parameter named product."""
    wanted = placeholders(entry.text) - INJECTED
    given = set(params)
    if given & INJECTED:
        raise CopyError(f"{entry.key}: product is injected, not passed")
    if wanted - given:
        raise CopyError(f"{entry.key}: missing parameter {sorted(wanted - given)}")
    if given - wanted:
        raise CopyError(f"{entry.key}: unused parameter {sorted(given - wanted)}")
    values = {k: _format_value(v) for k, v in params.items()}
    return entry.text.format(product=PRODUCT_NAME, **values)


def get(key, **params):
    try:
        entry = _entries()[key]
    except KeyError:
        raise CopyError(f"no copy entry {key}") from None
    return render(entry, params)


def claims():
    """{claim ID: entry key} for every entry with a claim."""
    return {e.claim: e.key for e in _entries().values() if e.claim}


def all_entries():
    return list(_entries().values())
