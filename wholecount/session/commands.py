"""Commands and the one undo stack (SPEC 3.4, 8.5, H13). Every change is a command with apply, undo, a plain label, an H8-safe
audit entry and the nodes it makes stale.

After a decision, results recompute before the command returns. A set-up change only marks nodes stale and waits for
Process (10.4). Undo pops the last command of any kind and recomputes before returning (C-04, C-14). There is no redo.
"""
import hashlib
from dataclasses import dataclass, field

from wholecount.engine.outputs.audit_entry import entry
from wholecount.engine.review import keep_one_per_program
from wholecount.session import reviewer as rv
from wholecount.session import staleness
from wholecount.session.decisions import make
from wholecount.session.state import _MISSING


@dataclass(frozen=True)
class CopyRef:
    key: str
    params: tuple = ()                    # (name, int)


@dataclass(frozen=True)
class CommandResult:
    ok: bool = True
    counts: tuple = ()                    # (name, int) the screen may show


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class History:
    def __init__(self, session):
        self.session = session
        self.stack = []

    def execute(self, cmd):
        s = self.session
        before = s.live_fingerprints()
        result = cmd.apply(s)
        self.stack.append(cmd)
        s.log(cmd.audit_entry())
        self._after(before, cmd)
        s.autosave()
        return result

    def undo(self):
        """Pop the last command of any kind. Returns its label, or None when there is nothing to undo."""
        if not self.stack:
            return None
        s = self.session
        cmd = self.stack.pop()
        before = s.live_fingerprints()
        cmd.undo(s)
        undone = [d.decision_id for d in getattr(cmd, "added", ())] + [d.decision_id for d in getattr(cmd, "removed", ())]
        s.log(entry("UNDO", decision_id=undone or None, reviewer=s.reviewer or None))
        if not s.restore_if_cached():
            self._after(before, cmd)
        s.autosave()
        return cmd.label

    def _after(self, before, cmd):
        from wholecount.session.runner import recompute_from

        s = self.session
        if s.results is None or isinstance(cmd, SetupChange):
            return
        live = s.live_fingerprints()
        changed = {n for n in staleness.NODES if live[n] != before[n]}
        first = staleness.earliest(changed | set(s.stale))
        # A set-up change still waiting for Process keeps everything after it stale; a decision doesn't run it quietly.
        if first is not None and staleness.NODES.index(first) >= staleness.NODES.index("decisions"):
            recompute_from(s, first)


DOWNSTREAM_DECISIONS = staleness.downstream("decisions")


class _DecisionCommand:
    """A command that adds decisions. Undo removes exactly the ones it added."""
    invalidates = DOWNSTREAM_DECISIONS
    code = "DECISION"

    def __init__(self):
        self.added = []
        self.removed = []

    def build(self, s):
        raise NotImplementedError

    def apply(self, s):
        self.added = s.decisions.add(self.build(s))
        return CommandResult(True, (("decisions", len(self.added)),))

    def undo(self, s):
        s.decisions.remove(self.added)
        s.decisions.add(self.removed)

    def _entry(self, code, **extra):
        d = self.added[0] if self.added else None
        return entry(code, decision_id=[x.decision_id for x in self.added][:1] or None, count=len(self.added),
                     reviewer=(d.reviewer if d else None) or None, second_reviewer=d.second_reviewer if d else None,
                     time_iso=d.made_at if d else None, **extra)

    def audit_entry(self):
        return self._entry(self.code)


def _mk(s, kind, record_keys, basis, person_keys=(), second=None, detail=()):
    return make(kind, record_keys, basis, s.now_iso(), s.reviewer, person_keys, second, detail)


def _open_reason_rows(s, reason_id):
    return [k for k, o in s.results.outcomes.items() if reason_id in o.reasons]


class ApproveRows(_DecisionCommand):
    """Approve rows, closing one reason (or all of them with "*"). A row can't be approved twice for one reason."""
    code = "APPROVE"

    def __init__(self, record_keys, reason_id="*", second=None):
        super().__init__()
        if reason_id == "same_id_conflict":
            raise Refused("decision_not_allowed")
        self.record_keys, self.reason_id, self.second = tuple(sorted(record_keys)), reason_id, second
        self.label = CopyRef("commands.approve_rows", (("count", len(self.record_keys)),))

    def build(self, s):
        rv.check_second(len(self.record_keys), self.second, s.reviewer)
        return [_mk(s, "approve", (k,), self.reason_id, second=self.second) for k in self.record_keys]


class AcceptGroup(_DecisionCommand):
    """Accept every row of one reason. Needs the typed count and a reason, and a second reviewer over 200 rows (8.7)."""
    code = "ACCEPT_GROUP"

    def __init__(self, reason_id, record_keys, proof, second=None):
        super().__init__()
        self.reason_id, self.record_keys, self.proof, self.second = reason_id, tuple(sorted(record_keys)), proof, second
        self.label = CopyRef("commands.accept_group", (("count", len(self.record_keys)),))

    def build(self, s):
        rv.check_accept(len(self.record_keys), self.proof, self.second, s.reviewer)
        detail = (("typed_count", str(self.proof.typed_count)), ("reason_code", self.proof.reason_code))
        return [_mk(s, "approve", (k,), self.reason_id, second=self.second, detail=detail) for k in self.record_keys]

    def audit_entry(self):
        return self._entry("ACCEPT_GROUP", typed_count=self.proof.typed_count, reason_code=self.proof.reason_code)


class SetAsideRows(_DecisionCommand):
    code = "SET_ASIDE"

    def __init__(self, record_keys, reason_code, note=None):
        super().__init__()
        if reason_code not in rv.SET_ASIDE_REASONS:
            raise Refused("reason_missing")
        if note is not None and (reason_code != "other" or len(note) > rv.settings()["note_max"]):
            raise Refused("note_not_allowed")
        self.record_keys, self.reason_code, self.note = tuple(sorted(record_keys)), reason_code, note
        self.label = CopyRef("commands.set_aside_rows", (("count", len(self.record_keys)),))

    def build(self, s):
        detail = (("note", self.note),) if self.note else ()
        return [_mk(s, "set_aside", (k,), self.reason_code, detail=detail) for k in self.record_keys]

    def audit_entry(self):
        return self._entry("SET_ASIDE", reason_code=self.reason_code, note=self.note)


class AcceptFills(_DecisionCommand):
    """Accept the fill proposals shown for these rows (P-GEO-9). Nothing changes until this runs."""
    code = "ACCEPT_FILL"

    def __init__(self, record_keys):
        super().__init__()
        self.record_keys = tuple(sorted(record_keys))
        self.label = CopyRef("commands.accept_fills", (("count", len(self.record_keys)),))

    def build(self, s):
        out = []
        for k in self.record_keys:
            props = s.results.fills.get(k, ())
            if props:
                basis = "|".join(sorted(p.basis for p in props))
                out.append(_mk(s, "accept_fill", (k,), hashlib.sha256(basis.encode()).hexdigest()[:12],
                               detail=tuple(("fill", p.basis) for p in props) + tuple(("field", p.field) for p in props)))
        return out


def _group(s, group_id):
    g = next((g for g in s.results.groups if g.group_id == group_id), None)
    if g is None:
        raise Refused("group_changed")
    return g


class KeepOneInCopyGroup(_DecisionCommand):
    code = "KEEP_ONE"

    def __init__(self, group_id, kept):
        super().__init__()
        self.group_id, self.kept = group_id, kept
        self.label = CopyRef("commands.keep_one", ())

    def build(self, s):
        from wholecount.engine.copies import KeepOne, apply_copy_decision

        g = _group(s, self.group_id)
        apply_copy_decision(g, KeepOne(self.kept))
        return [_mk(s, "keep_one", g.members, g.group_id, detail=(("kept", self.kept),))]


class MarkNotCopies(_DecisionCommand):
    code = "NOT_COPIES"

    def __init__(self, group_id):
        super().__init__()
        self.group_id = group_id
        self.label = CopyRef("commands.not_copies", ())

    def build(self, s):
        from wholecount.engine.copies import NotCopies, apply_copy_decision

        g = _group(s, self.group_id)
        apply_copy_decision(g, NotCopies())
        return [_mk(s, "not_copies", g.members, g.group_id, detail=(("verdict", "different"),))]


class DecideSameIdConflict(_DecisionCommand):
    code = "SAME_ID"

    def __init__(self, group_id, choice, split_rows=()):
        super().__init__()
        if choice not in ("different_people", "approved_as_entered"):
            raise Refused("decision_not_allowed")
        self.group_id, self.choice, self.split_rows = group_id, choice, tuple(sorted(split_rows))
        self.label = CopyRef(f"commands.{choice}", ())

    def build(self, s):
        g = _group(s, self.group_id)
        if g.kind != "same_id_different":
            raise Refused("decision_not_allowed")
        return [_mk(s, self.choice, g.members, g.group_id, detail=tuple(("split", k) for k in self.split_rows))]

    def audit_entry(self):
        return self._entry("SAME_ID", reason_code=self.choice)


class KeepOnePerProgram(_DecisionCommand):
    """REV-3: one decision per open copy group, keeping one row per program."""
    code = "KEEP_ONE_PER_PROGRAM"

    def __init__(self, selection):
        super().__init__()
        self.selection = tuple(sorted(selection))
        self.result = None
        self.label = CopyRef("commands.keep_one_per_program", ())

    def build(self, s):
        r = s.results
        self.result = keep_one_per_program(self.selection, r.open_groups,
                                           {k: r.rows[k].value("Program") for k in self.selection if k in r.rows})
        aside = dict(self.result.set_aside)
        out = []
        for g in r.open_groups:
            kept = [m for m in g.members if m in self.result.kept]
            gone = [m for m in g.members if m in aside]
            if kept and gone:
                out.append(_mk(s, "keep_one", g.members, g.group_id,
                               detail=tuple(("kept", k) for k in kept) + tuple(("aside_of", f"{m}>{aside[m]}") for m in gone)))
        return out

    def audit_entry(self):
        r = self.result
        return entry("KEEP_ONE_PER_PROGRAM", count=[len(r.kept), len(r.set_aside), len(r.left_alone)] if r else None,
                     reviewer=self.added[0].reviewer if self.added else None)


class SendToRowByRow(_DecisionCommand):
    code = "ROUTE"

    def __init__(self, reason_id):
        super().__init__()
        self.reason_id = reason_id
        self.label = CopyRef("commands.send_to_row_by_row", ())

    def build(self, s):
        return [_mk(s, "route", (), self.reason_id)]

    def audit_entry(self):
        return self._entry("ROUTE", reason_code=self.reason_id)


class ReturnToOpen(_DecisionCommand):
    """CMD-3: remove the earlier decisions on these rows. Undo puts them back."""
    code = "RETURN_TO_OPEN"

    def __init__(self, record_keys):
        super().__init__()
        self.record_keys = tuple(sorted(record_keys))
        self.label = CopyRef("commands.return_to_open", (("count", len(self.record_keys)),))

    def build(self, s):
        return []

    def apply(self, s):
        self.removed = s.decisions.touching(self.record_keys)
        s.decisions.remove(self.removed)
        return CommandResult(True, (("decisions", len(self.removed)),))

    def audit_entry(self):
        return entry("RETURN_TO_OPEN", count=len(self.removed), decision_id=[d.decision_id for d in self.removed] or None)


class DecidePair(_DecisionCommand):
    code = "PAIR"
    invalidates = staleness.downstream("identity")

    def __init__(self, a, b, verdict, second=None):
        super().__init__()
        if verdict not in ("same", "different"):
            raise Refused("decision_not_allowed")
        self.pair, self.verdict, self.second = tuple(sorted((a, b))), verdict, second
        self.label = CopyRef(f"commands.pair_{verdict}", ())
        self.masters = (None, None)

    def build(self, s):
        from wholecount.session.runner import _facts, pair_basis

        r = s.results
        a, b = self.pair
        if self.verdict == "same":
            ga, gb = r.identity.master_of[a], r.identity.master_of[b]
            records = sum(1 for k, m in r.identity.master_of_record.items() if m in (ga, gb))
            rv.check_second(records, self.second, s.reviewer, rv.settings()["second_signoff_join_records"])
        rows = {}
        for rk, pk in r.person_of_record.items():
            rows.setdefault(pk, []).append(rk)
        from wholecount.engine import pipeline as pl

        facts = {pk: _facts([pl.person_row(r.rows[rk], r.system_of_record[rk], pk) for rk in rows[pk]]) for pk in self.pair}
        self.masters = (r.identity.master_of.get(a), r.identity.master_of.get(b))
        return [_mk(s, "pair", (), pair_basis(facts[a], facts[b]), person_keys=self.pair, second=self.second,
                    detail=(("verdict", self.verdict),))]

    def audit_entry(self):
        return self._entry("PAIR", master_id=[m for m in self.masters if m] or None, reason_code=self.verdict)


class DecideProgramGroup(_DecisionCommand):
    code = "PROGRAM"
    invalidates = staleness.downstream("programs")

    def __init__(self, kind, members, label=None):
        super().__init__()
        self.kind, self.members, self.group_label = kind, tuple(sorted(members)), label
        self.label = CopyRef(f"commands.program_{kind}", (("count", len(self.members)),))

    def build(self, s):
        detail = (("program_kind", self.kind),) + tuple(("program", m) for m in self.members)
        if self.group_label:
            detail += (("label", self.group_label),)
        return [_mk(s, "program", (), "|".join(self.members) + "|" + self.kind, detail=detail)]

    def audit_entry(self):
        return self._entry("PROGRAM", program_name=list(self.members), reason_code=self.kind)


class ApplyCorrections(_DecisionCommand):
    """Corrections M09 verified. The text stays in memory; the decision holds keys, field names and the file fingerprint."""
    code = "CORRECTION"

    def __init__(self, corrections, fingerprint, file_name=None):
        super().__init__()
        self.corrections, self.fingerprint, self.file_name = tuple(corrections), fingerprint, file_name
        self.report = None
        self.hashes = ()
        self.label = CopyRef("commands.apply_corrections", (("count", len(self.corrections)),))

    def build(self, s):
        from wholecount.engine import pipeline as pl
        from wholecount.engine.corrections import apply_corrections
        from wholecount.session.keys import value_hash

        r = s.results
        records = {k: (row, r.outcomes[k].set_aside_reason is not None) for k, row in r.rows.items()}

        def restd(rk, values):
            for w in r.works:
                for i in w.inputs:
                    if i.record_key == rk:
                        return pl.restandardize(i, values, s.schema(), w.contexts, s.today())
            raise KeyError(rk)

        self.report = apply_corrections(self.corrections, records, self.fingerprint, restd)
        self.hashes = tuple((rk, f, value_hash(s.secret, f, old), value_hash(s.secret, f, new))
                            for rk, f, old, new in self.report.old_new)
        if not self.report.accepted:
            return []
        keys_ = tuple(rk for rk, _ in self.report.accepted)
        fields = tuple(sorted({f for _, fs in self.report.accepted for f in fs}))
        d = _mk(s, "correction", keys_, self.fingerprint, detail=tuple(("field", f) for f in fields))
        texts = {rk: {f: t for f, t in c.fields if f in dict(self.report.accepted)[rk]} for c in self.corrections
                 for rk in [c.record_key] if rk in dict(self.report.accepted)}
        s.correction_texts[d.decision_id] = texts
        return [d]

    def undo(self, s):
        for d in self.added:
            s.correction_texts.pop(d.decision_id, None)
        super().undo(s)

    def audit_entry(self):
        return entry("CORRECTION", record_key=[rk for rk, _, _, _ in self.hashes] or None,
                     field_name=[f for _, f, _, _ in self.hashes] or None,
                     old_hash=[o for _, _, o, _ in self.hashes] or None, new_hash=[n for _, _, _, n in self.hashes] or None,
                     count=len(self.hashes), file_name=self.file_name)


class AcknowledgeLowConfidence:
    invalidates = frozenset()

    def __init__(self):
        self.label = CopyRef("commands.acknowledge_low_confidence", ())
        self.previous = None
        self.measures = ()
        self.time = None

    def apply(self, s):
        self.previous = s.acknowledged
        self.measures = s.results.confidence.measures
        self.time = s.now_iso()
        s.acknowledged = (s.results.version, self.measures)
        return CommandResult()

    def undo(self, s):
        s.acknowledged = self.previous

    def audit_entry(self):
        nums = [n for _, n, _ in self.measures if n is not None]
        return entry("LOW_CONFIDENCE_ACKNOWLEDGED", count=nums or None, time_iso=self.time)


class SetReviewer:
    invalidates = frozenset()

    def __init__(self, name):
        self.name = rv.clean_name(name)
        self.previous = None
        self.label = CopyRef("commands.set_reviewer", ())

    def apply(self, s):
        self.previous = s.reviewer
        s.reviewer = self.name
        return CommandResult()

    def undo(self, s):
        s.reviewer = self.previous

    def audit_entry(self):
        return entry("REVIEWER", reviewer=self.name)


class FinishReview:
    invalidates = frozenset()

    def __init__(self, confirmed_open_rows):
        self.confirmed = confirmed_open_rows
        self.previous = None
        self.label = CopyRef("commands.finish_review", (("count", confirmed_open_rows),))
        self.reviewer = None

    def apply(self, s):
        from wholecount.engine.review import finish_gate

        r = s.results
        gate = finish_gate(list(r.outcomes.values()), r.open_groups, r.replay.routed)
        if gate.held:
            raise Refused("finish_held")
        if gate.open_rows != self.confirmed:
            raise Refused("count_mismatch")
        self.previous = s.finished
        self.reviewer = s.reviewer
        s.finished = (r.version, self.confirmed, s.reviewer)
        return CommandResult()

    def undo(self, s):
        s.finished = self.previous

    def audit_entry(self):
        return entry("FINISH_REVIEW", count=self.confirmed, reviewer=self.reviewer or None)


class SetupChange:
    """A change to one set-up section. It only marks nodes stale; Process re-runs them (10.4)."""

    def __init__(self, section, key, new_value):
        from wholecount.session.state import SECTIONS

        if section not in SECTIONS:
            raise Refused("unknown_section")
        self.section, self.key, self.new = section, key, new_value
        self.old = _MISSING
        self.invalidates = staleness.downstream(staleness.SECTION_NODE[section])
        self.label = CopyRef(f"commands.setup.{section}", ())

    def apply(self, s):
        self.old = s.setup.set(self.section, self.key, self.new)
        return CommandResult()

    def undo(self, s):
        s.setup.set(self.section, self.key, self.old)

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code=self.section)


class AddSources:
    """Add several files in one step, so one Undo takes them all back (SPEC 5.1)."""

    invalidates = staleness.downstream("sources")

    def __init__(self, paths):
        self.paths = tuple(str(p) for p in paths)
        self.old = {}
        self.label = CopyRef("commands.add_sources", (("count", len(self.paths)),))

    def apply(self, s):
        self.old = {p: s.setup.set("sources", p, True) for p in self.paths}
        return CommandResult()

    def undo(self, s):
        for p, v in self.old.items():
            s.setup.set("sources", p, v)

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code="sources", count=len(self.paths))


class UseExampleData:
    """Load the example files with the sample reference beside them (P-GEO-4a). The run is practice from then on."""

    invalidates = staleness.downstream("sources")

    def __init__(self, paths, backend):
        self.add = AddSources(paths)
        self.backend = backend
        self.old = None
        self.label = CopyRef("commands.use_example_data", ())

    def apply(self, s):
        self.old = (s.backend, s.allow_sample)
        s.backend, s.allow_sample = self.backend, True
        return self.add.apply(s)

    def undo(self, s):
        self.add.undo(s)
        s.backend, s.allow_sample = self.old

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code="example_data", count=len(self.add.paths))


class SetKeepSensitive:
    """Keep or drop one sensitive column at load (P-READ-9). The file is read again; a dropped column isn't held."""

    invalidates = staleness.downstream("sources")

    def __init__(self, column, keep):
        self.column, self.keep = column, bool(keep)
        self.old = None
        self.label = CopyRef("commands.keep_sensitive" if keep else "commands.drop_sensitive", ())

    def apply(self, s):
        self.old = s.keep_sensitive
        s.keep_sensitive = (s.keep_sensitive | {self.column}) if self.keep else (s.keep_sensitive - {self.column})
        return CommandResult()

    def undo(self, s):
        s.keep_sensitive = self.old

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code="sensitive_kept" if self.keep else "sensitive_dropped")


class ConfirmTable:
    """Match your columns: this table's matching is confirmed. A view fact; it changes no result."""

    invalidates = frozenset()

    def __init__(self, table, confirmed=True):
        self.table, self.confirmed = tuple(table), confirmed
        self.was = None
        self.label = CopyRef("commands.confirm_table", ())

    def apply(self, s):
        self.was = self.table in s.confirmed_tables
        (s.confirmed_tables.add if self.confirmed else s.confirmed_tables.discard)(self.table)
        return CommandResult()

    def undo(self, s):
        (s.confirmed_tables.add if self.was else s.confirmed_tables.discard)(self.table)

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code="table_confirmed")


class LoadSetup:
    """Apply a saved set-up, whole or only what fits the files loaded now (SPEC 10.3). One Undo takes it back."""

    invalidates = staleness.downstream("tables")

    def __init__(self, setup_json_, name=""):
        self.data = setup_json_
        self.before = None
        self.label = CopyRef("commands.load_setup", ())

    def apply(self, s):
        import copy as _copy

        from wholecount.session.store import apply_setup_json

        self.before = _copy.deepcopy({k: dict(v) for k, v in s.setup.sections.items()})
        apply_setup_json(s.setup, self.data)
        return CommandResult()

    def undo(self, s):
        for k, v in self.before.items():
            s.setup.sections[k] = v

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code="setup_loaded")


class ConfirmStage:
    """Continue on Tidy up: the steps as they stand are kept (the strip then reads {n} steps kept). A view fact."""

    invalidates = frozenset()

    def __init__(self, stage_id):
        self.stage_id = stage_id
        self.was = None
        self.label = CopyRef("commands.confirm_stage", ())

    def apply(self, s):
        self.was = self.stage_id in s.confirmed_stages
        s.confirmed_stages.add(self.stage_id)
        return CommandResult()

    def undo(self, s):
        if not self.was:
            s.confirmed_stages.discard(self.stage_id)

    def audit_entry(self):
        return entry("SETUP_CHANGE", reason_code=f"{self.stage_id}_confirmed")


class WithdrawProgramDecision(_DecisionCommand):
    """Take back one program decision, such as one confirmation, without undoing what came after it (P-PROG-3)."""

    code = "PROGRAM"
    invalidates = staleness.downstream("programs")

    def __init__(self, decision_id):
        super().__init__()
        self.decision_id = decision_id
        self.label = CopyRef("commands.program_withdraw", ())

    def apply(self, s):
        d = next(x for x in s.decisions if x.decision_id == self.decision_id)
        s.decisions.remove([d])
        self.removed = [d]
        return CommandResult()

    def audit_entry(self):
        return entry("PROGRAM", decision_id=[self.decision_id], reason_code="withdrawn")


ALL_COMMANDS = (ApproveRows, AcceptGroup, SetAsideRows, AcceptFills, KeepOneInCopyGroup, MarkNotCopies, DecideSameIdConflict,
                KeepOnePerProgram, SendToRowByRow, ReturnToOpen, DecidePair, DecideProgramGroup, ApplyCorrections,
                AcknowledgeLowConfidence, SetReviewer, FinishReview, SetupChange, AddSources, UseExampleData,
                SetKeepSensitive, ConfirmTable, LoadSetup, ConfirmStage, WithdrawProgramDecision)


class JobCommand:
    """A finished job's apply and undo as one command, so one Undo takes back the whole job (SPEC 11.6.1). The job's run
    happened on the worker; apply runs here on the main thread."""

    invalidates = frozenset()

    def __init__(self, job, result):
        self.job, self.result = job, result
        self.label = CopyRef(f"action.{job.action_id}", ())
        self.token = None

    def apply(self, s):
        self.token = self.job.apply(s, self.result)
        return CommandResult()

    def undo(self, s):
        self.job.undo(s, self.token)

    def audit_entry(self):
        return entry("JOB", reason_code=self.job.action_id)
