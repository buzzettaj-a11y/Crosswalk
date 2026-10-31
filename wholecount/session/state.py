"""The session (SPEC 3.4): the set-up, the decisions, the reviewer, one undo stack and the derived Results.

Results are derived and versioned. Nothing shows or writes counts while a node is stale or a balance fails (COUNT-6).
"""
import datetime as dt
import getpass
import hashlib
import pathlib
from dataclasses import dataclass, field

from wholecount.engine.counts import BalanceError, assert_balance
from wholecount.session import staleness
from wholecount.session.decisions import DecisionStore
from wholecount.session.reviewer import current_reviewer

SECTIONS = ("sources", "tables", "steps", "schema", "mappings", "defaults", "date_orders", "program_columns", "run_settings",
            "export_settings")


class Setup:
    """The set-up sections, each a dict. A table is named by (file name, its index in that file) so a header change keeps
    the operator's choices attached to it."""

    def __init__(self, paths=()):
        self.sections = {s: {} for s in SECTIONS}
        for p in paths:
            self.sections["sources"][str(p)] = True

    def get(self, section, key, default=None):
        return self.sections[section].get(key, default)

    def set(self, section, key, value):
        """Set a value and return the old one (or the _MISSING marker)."""
        old = self.sections[section].get(key, _MISSING)
        if value is _MISSING:
            self.sections[section].pop(key, None)
        else:
            self.sections[section][key] = value
        return old

    def items(self, section):
        return sorted(self.sections[section].items(), key=lambda kv: repr(kv[0]))

    def stable(self, *sections):
        return repr([(s, [(repr(k), repr(v)) for k, v in self.items(s)]) for s in sections])

    def paths(self):
        return [pathlib.Path(p) for p, inc in self.sections["sources"].items() if inc]


class _Missing:
    def __repr__(self):
        return "<unset>"


_MISSING = _Missing()


@dataclass
class Results:
    version: int
    fingerprints: dict
    outcomes: dict                        # record key -> RowOutcome
    rows: dict                            # record key -> StdRow (memory only)
    works: list
    groups: tuple                         # every copy group
    open_groups: tuple
    identity: object
    person_of_record: dict
    file_of_record: dict
    system_of_record: dict
    program_names: tuple
    program_proposals: tuple
    program_map: object
    program_of_record: dict
    counts: object
    balance: object
    confidence: object
    placements: dict
    fills: dict
    replay: object
    no_longer_apply: tuple
    kept: int
    lapsed: int
    practice: bool = False
    release: str = ""
    backend: str = "none"
    load: object = field(default=None, repr=False)

    def digest(self):
        """A hash over what the screens and files would show, so equal digests mean equal results."""
        parts = [repr(sorted((k, o.count_status.value, o.reasons, o.set_aside_reason, o.kept_record_key,
                              None if o.location is None else (o.location.kind, o.location.confidence, o.location.reason,
                                                               o.location.filled))
                             for k, o in self.outcomes.items())),
                 repr(sorted(self.identity.master_of_record.items())), repr(self.counts), repr(self.confidence),
                 repr(sorted(self.program_of_record.items()))]
        return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DownloadGate:
    held: bool
    reasons: tuple = ()


class Session:
    def __init__(self, secret, paths=(), backend=None, districts=None, clock=None, today=None, getuser=getpass.getuser,
                 allow_sample=False, keep_sensitive=frozenset(), schema=None):
        from wholecount.engine.geo.backend import GeoOptions, NoBackend
        from wholecount.engine.schema import default_schema
        from wholecount.session.commands import History

        self.secret = secret
        self.setup = Setup(paths)
        self.setup.sections["schema"]["schema"] = schema or default_schema()
        self.setup.sections["run_settings"]["extra_fields"] = GeoOptions().extra_fields
        self.backend = backend or NoBackend()
        self.districts = districts
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.today = today or (lambda: self.clock().date())
        self.allow_sample = allow_sample
        self.keep_sensitive = frozenset(keep_sensitive)
        self.decisions = DecisionStore()
        self.reviewer = current_reviewer(getuser)
        self.history = History(self)
        self.results = None
        self.recent = []                  # the last three Results, by fingerprint (STALE-3)
        self.correction_texts = {}        # decision ID -> {record key: {field: text}}, memory only
        self.acknowledged = None          # (results version, measures) of the last low-confidence tick
        self.finished = None
        self.stage = "sources"            # the stage ID the window shows, kept in saved progress (A-19)
        self.audit_log = []               # (time ISO, AuditEntry), append only (AUD-1)
        self.store = None                 # a session.store.Store when saved progress is wanted (STORE-3)
        self.session_id = hashlib.sha256(self.now_iso().encode("utf-8")).hexdigest()[:16]
        self._load_cache = None

    @property
    def audit(self):
        return [e for _, e in self.audit_log]

    def log(self, entry):
        self.audit_log.append((self.now_iso(), entry))

    def autosave(self):
        """STORE-3: after each command, when a store is attached and saved progress is on."""
        if self.store is not None and self.results is not None:
            from wholecount.session.store import snapshot
            return self.store.save(self.session_id, snapshot(self))
        return None

    # Time comes from the injected clock (H3).
    def now_iso(self):
        return self.clock().astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def schema(self):
        return self.setup.get("schema", "schema")

    def own_inputs(self):
        s = self.setup
        review = [d for d in self.decisions if d.kind not in ("pair", "program")]
        return {
            "sources": s.stable("sources"),
            "tables": s.stable("tables"),
            "steps": s.stable("steps"),
            "mappings": s.stable("schema", "mappings"),
            "standardized": s.stable("defaults", "date_orders") + repr(self.today()),
            "geo": s.stable("run_settings") + repr((self.backend.name, self.backend.release, self.allow_sample)),
            "decisions": repr(sorted(d.decision_id for d in review)) + repr(sorted(self.correction_texts)),
            "identity": repr(sorted(d.decision_id for d in self.decisions.of_kind("pair"))),
            "programs": repr(sorted(d.decision_id for d in self.decisions.of_kind("program"))) + s.stable("program_columns"),
            "exports": s.stable("export_settings"),
        }

    def live_fingerprints(self):
        return staleness.fingerprints(self.own_inputs())

    @property
    def stale(self):
        return staleness.stale(self.live_fingerprints(), self.results.fingerprints if self.results else None)

    def counts(self):
        """COUNT-6: counts only when nothing is stale and both balances hold."""
        st = self.stale
        if st:
            raise staleness.StaleResults(st)
        assert_balance(self.results.balance, self.results.outcomes.values())
        return self.results.counts

    def download_gate(self):
        reasons = []
        if self.stale:
            reasons.append("stale")
        else:
            try:
                assert_balance(self.results.balance, self.results.outcomes.values())
            except BalanceError:
                reasons.append("balance_failed")
            conf = self.results.confidence
            if conf.level == "low" and (self.acknowledged is None or self.acknowledged[0] != self.results.version):
                reasons.append("low_confidence_unacked")
        return DownloadGate(bool(reasons), tuple(reasons))

    def preflight(self, environ=None, data_dir=None):
        import os

        from wholecount.engine.geo.backend import preflight
        from wholecount.paths import data_dir as default_dir

        return preflight(environ if environ is not None else os.environ, data_dir or default_dir(), self.today())

    def remember(self, results):
        self.results = results
        self.recent = [r for r in self.recent if r.fingerprints != results.fingerprints][-2:] + [results]

    def restore_if_cached(self):
        """STALE-3: when the live fingerprints match a recent result, it comes back without a re-run."""
        live = self.live_fingerprints()
        for r in reversed(self.recent):
            if r.fingerprints == live:
                self.results = r
                return True
        return False
