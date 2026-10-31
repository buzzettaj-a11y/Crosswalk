"""Saved set-ups for the window (SPEC 10.3): the list, a fit report against the files loaded now, and loading what fits.
A set-up holds column names, steps, mappings, defaults and program names, never client data."""
import datetime as dt
import pathlib
from dataclasses import dataclass

from wholecount.session.store import SETUP_SECTIONS, decode


@dataclass(frozen=True)
class SavedSetup:
    path: pathlib.Path
    name: str
    saved_at: dt.datetime
    file_names: tuple


@dataclass(frozen=True)
class Fit:
    fits: tuple                           # file names the set-up was made for that are loaded now
    missing: tuple                        # file names it names that aren't loaded

    @property
    def whole(self):
        return not self.missing


def _file_names(setup_json_):
    names = set()
    for section in SETUP_SECTIONS:
        for k, _ in setup_json_.get(section, []):
            key = decode(k)
            if isinstance(key, tuple) and key and isinstance(key[0], str) and "." in key[0]:
                names.add(key[0])
    return tuple(sorted(names))


def saved_setups(store):
    if store is None or not store.setups.exists():
        return ()
    out = []
    for p in sorted(store.setups.glob("*.wcsetup")):
        try:
            data = store.load_setup(p)
        except Exception:  # noqa: BLE001  an unreadable set-up is skipped, never shown half
            continue
        when = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc)
        out.append(SavedSetup(p, data.get("name", ""), when, _file_names(data.get("setup", {}))))
    return tuple(sorted(out, key=lambda s: s.saved_at, reverse=True))


def fit(saved_json, loaded_names):
    names = _file_names(saved_json)
    loaded = set(loaded_names)
    return Fit(tuple(n for n in names if n in loaded), tuple(n for n in names if n not in loaded))


def fitting_part(saved_json, loaded_names):
    """Only the entries for loaded files, plus the entries that name no file (the schema, run settings)."""
    loaded = set(loaded_names)
    out = {}
    for section in SETUP_SECTIONS:
        keep = []
        for k, v in saved_json.get(section, []):
            key = decode(k)
            named = isinstance(key, tuple) and key and isinstance(key[0], str) and "." in key[0]
            if not named or key[0] in loaded:
                keep.append([k, v])
        out[section] = keep
    return out
