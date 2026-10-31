"""Saved progress and set-ups (SPEC 10.1 to 10.3, A-04, A-08, fix plan 4.2). Encrypted with DPAPI for this Windows user.

A saved file is `WCS1`, the SHA-256 of the protected blob, then the blob. It holds the set-up, the decisions and, per source,
the file name, normalized name, fingerprint and system. Never cell values, rows, corrections text or the install secret.
"""
import dataclasses
import datetime as dt
import enum
import hashlib
import importlib
import json
import os
import pathlib

from wholecount.brand import VERSION
from wholecount.session.decisions import Decision
from wholecount.settings.loader import load as load_settings

MAGIC = b"WCS1"
FORMAT = 1
SETUP_FORMAT = 1
PREFS = "prefs.json"
SETUP_SECTIONS = ("tables", "steps", "schema", "mappings", "defaults", "date_orders", "program_columns", "run_settings",
                  "export_settings")
# Only these classes come back from a saved file; anything else is refused.
ALLOWED_CLASSES = frozenset({
    "wholecount.engine.schema.Schema", "wholecount.engine.schema.Field", "wholecount.engine.schema.FieldType",
    "wholecount.engine.dateorder.DateFieldSetting", "wholecount.engine.dateorder.DateOrder", "wholecount.engine.dateorder.TwoDigitRule",
    "wholecount.engine.prepare.steps.Step",
})


class StoreError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _class_name(obj):
    return f"{type(obj).__module__}.{type(obj).__qualname__}"


def encode(value):
    """A tagged JSON form for set-up values: dataclasses, enums, tuples and frozensets of the allowed classes."""
    if isinstance(value, enum.Enum):
        return {"t": "enum", "c": _class_name(value), "v": value.value}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"t": "dc", "c": _class_name(value),
                "f": {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}}
    if isinstance(value, tuple):
        return {"t": "tuple", "v": [encode(v) for v in value]}
    if isinstance(value, frozenset):
        return {"t": "frozenset", "v": sorted((encode(v) for v in value), key=json.dumps)}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {"t": "dict", "v": [[encode(k), encode(v)] for k, v in value.items()]}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise StoreError("unsupported_value")


def _cls(name):
    if name not in ALLOWED_CLASSES:
        raise StoreError("unknown_value")
    module, _, qual = name.rpartition(".")
    return getattr(importlib.import_module(module), qual)


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    t = value.get("t")
    if t == "enum":
        return _cls(value["c"])(value["v"])
    if t == "dc":
        return _cls(value["c"])(**{k: decode(v) for k, v in value["f"].items()})
    if t == "tuple":
        return tuple(decode(v) for v in value["v"])
    if t == "frozenset":
        return frozenset(decode(v) for v in value["v"])
    if t == "dict":
        return {decode(k): decode(v) for k, v in value["v"]}
    raise StoreError("unknown_value")


def setup_json(setup, sections=SETUP_SECTIONS):
    return {s: [[encode(k), encode(v)] for k, v in setup.items(s)] for s in sections}


def apply_setup_json(setup, data, sections=SETUP_SECTIONS):
    for s in sections:
        setup.sections[s] = {decode(k): decode(v) for k, v in data.get(s, [])}


def decision_json(d):
    return {f.name: (list(map(list, v)) if f.name == "detail" else list(v) if isinstance(v, tuple) else v)
            for f in dataclasses.fields(d) for v in [getattr(d, f.name)]}


def decision_from_json(d):
    return Decision(d["decision_id"], d["kind"], tuple(d["record_keys"]), tuple(d["person_keys"]), d["basis"], d["made_at"],
                    d["reviewer"], d.get("second_reviewer"), tuple(tuple(x) for x in d.get("detail", ())))


def snapshot(session):
    """The saved-progress JSON for a session. No cell value goes in."""
    from wholecount.session.keys import normalize_file_name

    load = session.results.load if session.results else None
    sources = []
    if load:
        systems = {w.table.letter: w.system for w in session.results.works}
        for o in load.files:
            if o.status == "ok":
                sources.append({"file_name": o.name, "normalized": normalize_file_name(o.name), "fingerprint": o.fingerprint,
                                "system": systems.get(o.letter, "")})
    return {"format": FORMAT, "app_version": VERSION, "saved_at": session.now_iso(), "setup": setup_json(session.setup),
            "decisions": [decision_json(d) for d in session.decisions], "sources": sources,
            "stage": getattr(session, "stage", "sources")}


class Store:
    """Saved progress and set-ups under one base folder (STORE-1), with injected DPAPI functions."""

    def __init__(self, base, protect=None, unprotect=None):
        from wholecount.session import dpapi

        self.base = pathlib.Path(base)
        self.protect = protect or dpapi.protect
        self.unprotect = unprotect or dpapi.unprotect

    @property
    def sessions(self):
        return self.base / "sessions"

    @property
    def setups(self):
        return self.base / "setups"

    # prefs.json holds settings only (H9).
    def prefs(self):
        p = self.base / PREFS
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"saved_progress": True}

    def set_saved_progress(self, on, session_id=None):
        prefs = self.prefs()
        prefs["saved_progress"] = bool(on)
        self.base.mkdir(parents=True, exist_ok=True)
        _atomic(self.base / PREFS, json.dumps(prefs, sort_keys=True).encode("utf-8"))
        if not on:
            for f in self.sessions.glob("*.wcs") if self.sessions.exists() else ():
                if session_id is None or f.stem == session_id:
                    f.unlink()

    def _pack(self, data):
        blob = self.protect(json.dumps(data, sort_keys=True).encode("utf-8"))
        return MAGIC + hashlib.sha256(blob).digest() + blob

    def _unpack(self, raw):
        if not raw.startswith(MAGIC) or len(raw) < len(MAGIC) + 32:
            raise StoreError("damaged")
        digest, blob = raw[4:36], raw[36:]
        if hashlib.sha256(blob).digest() != digest:
            raise StoreError("damaged")
        try:
            data = json.loads(self.unprotect(blob).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise StoreError("damaged") from None
        except Exception:
            raise StoreError("other_user") from None
        if data.get("format") != FORMAT:
            raise StoreError("unknown_version")
        return data

    def save(self, session_id, data):
        """STORE-3: through a temporary name and a rename."""
        if not self.prefs().get("saved_progress", True):
            return None
        self.sessions.mkdir(parents=True, exist_ok=True)
        path = self.sessions / f"{session_id}.wcs"
        _atomic(path, self._pack(data))
        return path

    def load(self, path):
        return self._unpack(pathlib.Path(path).read_bytes())

    def purge_expired(self, now, days=None):
        """STORE-4: delete saved progress older than saved_progress_days, by file time (contents need DPAPI)."""
        days = load_settings("limits")["saved_progress_days"] if days is None else days
        gone = 0
        for f in self.sessions.glob("*.wcs") if self.sessions.exists() else ():
            age = now.timestamp() - f.stat().st_mtime
            if age > days * 86400:
                f.unlink()
                gone += 1
        return gone

    # Set-ups (STORE-6).
    def save_setup(self, name, setup):
        self.setups.mkdir(parents=True, exist_ok=True)
        data = {"format": FORMAT, "setup_format": SETUP_FORMAT, "name": name, "setup": setup_json(setup)}
        path = self.setups / f"{hashlib.sha256(name.encode('utf-8')).hexdigest()[:16]}.wcsetup"
        _atomic(path, self._pack(data))
        return path

    def load_setup(self, path):
        return self._unpack(pathlib.Path(path).read_bytes())


def export_setup(setup, path):
    """Plain JSON: DPAPI output can't move to another computer. Column names, steps, mappings, defaults and program names."""
    data = {"setup_format": SETUP_FORMAT, "setup": setup_json(setup)}
    _atomic(pathlib.Path(path), json.dumps(data, sort_keys=True, indent=1).encode("utf-8"))


def import_setup(path, setup):
    """Validate the format, the keys and the value types, refuse unknown keys and oversize files, then apply."""
    p = pathlib.Path(path)
    if p.stat().st_size > load_settings("limits")["setup_max_bytes"]:
        raise StoreError("too_big")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise StoreError("damaged") from None
    if not isinstance(data, dict) or set(data) != {"setup_format", "setup"}:
        raise StoreError("unknown_key")
    if data["setup_format"] != SETUP_FORMAT:
        raise StoreError("unknown_version")
    body = data["setup"]
    if not isinstance(body, dict) or set(body) - set(SETUP_SECTIONS):
        raise StoreError("unknown_key")
    for s, items in body.items():
        if not isinstance(items, list) or not all(isinstance(kv, list) and len(kv) == 2 for kv in items):
            raise StoreError("wrong_type")
    decoded = {s: [(decode(k), decode(v)) for k, v in items] for s, items in body.items()}
    for s, items in decoded.items():
        setup.sections[s] = dict(items)
    return setup


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.part")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def file_age_days(path, now):
    return (now - dt.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime, tz=dt.timezone.utc)).days
