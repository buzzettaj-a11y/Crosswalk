"""Running the pipeline for a session (SPEC 6.10). The new state is built beside the old one and swapped at the end, so a
cancel leaves the session unchanged. A run never clears decisions (C-07); they replay by record key.
"""
import dataclasses
import hashlib

from wholecount.engine import pipeline as pl
from wholecount.engine.confidence import batch_confidence
from wholecount.engine.copies import key_modes
from wholecount.engine.counts import balance_of, count
from wholecount.engine.defaults import SourceDefault
from wholecount.engine.geo.backend import GeoOptions
from wholecount.engine.geo.place import place_rows
from wholecount.engine.identity import PairVerdict, load_settings, resolve, score_pair
from wholecount.engine.mapping import process_blocks
from wholecount.engine.programs import ProgramDecision, StopAtPrograms, fast_path_gate
from wholecount.engine.progress import NullSink
from wholecount.engine.read.sensitive import drop_sensitive
from wholecount.engine.read.tables import rebuild_with_header
from wholecount.engine.review import base_outcome, close_reasons
from wholecount.engine.systems import default_systems
from wholecount.session import keys
from wholecount.session.decisions import NoLongerApply, replay
from wholecount.session.loader import Cancelled, key_tables, load_files
from wholecount.session.state import Results


class Blocked(Exception):
    """The fast path can't run: a required field has no mapping (P-MAP-2). Carries the table key and field only."""

    def __init__(self, table_key, field):
        super().__init__(f"{field}")
        self.table_key = table_key
        self.field = field


def _load(session, sink):
    key = session.setup.stable("sources") + repr(sorted(session.keep_sensitive))
    if session._load_cache is not None and session._load_cache[0] == key:
        return session._load_cache[1]
    load = load_files(session.setup.paths(), sink, session.secret, keep=session.keep_sensitive)
    session._load_cache = (key, load)
    return load


def _tables(session, load):
    """Step 2: each readable file's tables, with the set-up's header rows and inclusion. Returns (all tables, file of table)."""
    out, file_of = [], {}
    for o in load.files:
        if o.status != "ok":
            continue
        mine = [t for t in load.tables if t.letter == o.letter]
        for idx, t in enumerate(mine):
            hr = session.setup.get("tables", (o.name, idx, "header_row"))
            if hr is not None and hr != t.header_row:
                t2 = key_tables(session.secret, o.file_key, [rebuild_with_header(t, hr)])[0]
                t2.letter = o.letter
                t = drop_sensitive(t2, session.keep_sensitive)
            inc = session.setup.get("tables", (o.name, idx, "included"))
            if inc is not None:
                t = dataclasses.replace(t, included=inc)
            out.append(t)
            file_of[t.key] = (o.name, idx)
    return out, file_of


def _accounting(load, tables):
    files = [o for o in load.files if o.status == "ok"]
    return {
        "excluded_rows": sum(t.excluded_row_count for t in tables),
        "non_table_rows": sum(o.accounting.non_table for o in files),
        "above_header_rows": sum(t.above_header_rows for t in tables),
        "header_rows": sum(1 for t in tables if t.header_row and not t.header_is_virtual),
        "file_rows": sum(o.accounting.non_empty_rows + o.accounting.shared_rows for o in files),
    }


def system_names(session, load):
    """Letter -> system name. A file joins another file's system, or keeps its own, from the set-up's systems section
    (SPEC 5.2). Names default to the file name without its extension."""
    ok = [o for o in load.files if o.status == "ok"]
    base = {s.letters[0]: s.display_name for s in default_systems([(o.letter, o.name) for o in ok])}
    by_name = {o.name: o.letter for o in ok}
    out = {}
    for o in ok:
        owner = session.setup.get("systems", ("member", o.name))
        owner_letter = by_name.get(owner, o.letter)
        owner_name = next(x.name for x in ok if x.letter == owner_letter)
        out[o.letter] = session.setup.get("systems", ("name", owner_name)) or base[owner_letter]
    return out


def _works(session, load, tables, file_of, sink):
    systems = system_names(session, load)
    schema = session.schema()
    works = []
    for t in tables:
        if not t.included:
            continue
        if sink.cancelled():
            raise Cancelled()
        name, idx = file_of[t.key]
        w = pl.TableWork(t, systems[t.letter], name)
        pl.prepare(w, schema, session.setup.get("steps", (name, idx)))
        overrides = tuple((f, c) for (fn, i, f), c in session.setup.items("mappings") if (fn, i) == (name, idx))
        pl.map_table(w, schema, overrides)
        defaults = tuple(SourceDefault(t.key, f, v) for (fn, i, f), v in session.setup.items("defaults") if (fn, i) == (name, idx))
        setting = session.setup.get("date_orders", (name, idx, "Date_of_Birth"))
        pl.standardize(w, schema, defaults, session.today(), setting)
        works.append(w)
    return works


def _facts(rows):
    def filled(r):
        return sum(1 for v in (r.first, r.last, r.dob, r.address_key, r.zip5) if v)
    return sorted(rows, key=lambda r: (-filled(r), r.record_key))[0]


def pair_basis(a, b):
    """A pair decision's basis: a hash of the evidence codes the two person records give, rare_name aside."""
    sc = score_pair(a, b, False, load_settings()["weights"])
    return hashlib.sha256("\x1f".join(sorted(sc.evidence)).encode("utf-8")).hexdigest()[:12]


def program_decision(d):
    return ProgramDecision(d.get("program_kind"), d.all("program"), d.get("label"), inherited=False)


def run(session, sink=None):
    sink = sink or NullSink()
    fps = session.live_fingerprints()
    load = _load(session, sink)
    tables, file_of = _tables(session, load)
    works = _works(session, load, tables, file_of, sink)
    rows = {r.record_key: r for w in works for r in w.rows}
    inputs = {i.record_key: (i, w) for w in works for i in w.inputs}
    system_of = {r.record_key: w.system for w in works for r in w.rows}
    file_name_of = {r.record_key: w.file_name for w in works for r in w.rows}
    options = GeoOptions(frozenset(session.setup.get("run_settings", "extra_fields", frozenset())))
    backend = session.backend

    def place(rs, with_sink):
        return place_rows(rs, backend, session.districts, options, sink if with_sink else None).results

    placement = place(list(rows.values()), True)
    fills = pl.fill_proposals(rows.values(), backend)
    groups, _ = pl.copies_step(works)
    same_id_rows = {m for g in groups if g.kind == "same_id_different" for m in g.members}
    outcomes = pl.base_outcomes(rows.values(), placement, same_id_rows)

    # Step 8, first pass: accepted fills and corrections change a row's text, so they are applied before the other decisions.
    first = replay(session.decisions, outcomes, groups, fills, session.correction_texts)
    changed = {}
    for rk, props in first.filled.items():
        changed[rk] = ({p.field: p.value for p in props}, False)
    for rk, texts in first.corrections.items():
        prev = changed.get(rk, ({}, False))[0]
        changed[rk] = ({**prev, **texts}, True)
    for rk, (values, corrected) in changed.items():
        row_input, w = inputs[rk]
        new = pl.restandardize(row_input, values, session.schema(), w.contexts, session.today())
        rows[rk] = new
        placement.update(place([new], False))
        o = pl.located(base_outcome(new, same_id_rows), new, placement)
        if rk in first.filled:
            o = dataclasses.replace(o, location=dataclasses.replace(o.location, filled=True)) if o.location else o
        outcomes[rk] = close_reasons(o, set(), corrected=corrected) if corrected else o
    rep = replay(session.decisions, outcomes, groups, fills, session.correction_texts)
    outcomes = rep.outcomes
    nla = list(rep.no_longer_apply)
    applied = set(rep.applied)

    # Step 9: identity over counted rows.
    counted = {rk for rk, o in outcomes.items() if o.counted}
    crow = {rk: pl.copy_row(rows[rk], system_of[rk]) for rk in counted}
    decided = set(rep.copy_decisions)
    modes = key_modes(groups, rep.copy_decisions, rep.split_rows, rows=[crow[rk] for rk in sorted(counted)])
    keyer = lambda **kw: keys.person_key(session.secret, **kw)  # noqa: E731
    person_of = {rk: pl.person_key_for(keyer, crow[rk], modes.get(rk)) for rk in counted}
    prows = [pl.person_row(rows[rk], system_of[rk], person_of[rk]) for rk in sorted(counted)]
    by_person = {}
    for p in prows:
        by_person.setdefault(p.person_key, []).append(p)
    verdicts = [PairVerdict(person_of[a], person_of[b], "different", d.decision_id, d.reviewer)
                for a, b, d in rep.verdict_pairs if a in person_of and b in person_of and person_of[a] != person_of[b]]
    for d in sorted(session.decisions.of_kind("pair"), key=lambda d: (d.made_at, d.decision_id)):
        a, b = d.person_keys
        if a not in by_person or b not in by_person:
            nla.append(NoLongerApply(d, "person_gone"))
            continue
        if d.basis != pair_basis(_facts(by_person[a]), _facts(by_person[b])):
            nla.append(NoLongerApply(d, "basis_changed"))
            continue
        verdicts.append(PairVerdict(a, b, d.get("verdict"), d.decision_id, d.reviewer))
        applied.add(d.decision_id)
    open_groups = tuple(g for g in groups if g.kind in ("identical", "possible") and g.group_id not in decided
                        and sum(1 for m in g.members if m in counted) > 1)
    xw = _crosswalk_read(session, backend, load, by_person, nla)
    if xw is not None:
        verdicts += list(xw.verdicts)
    identity = resolve(prows, verdicts, known=xw.known if xw else None,
                       open_copy_groups=[tuple(m for m in g.members if m in counted) for g in open_groups])

    # Step 10: programs.
    pdecs = sorted(session.decisions.of_kind("program"), key=lambda d: (d.made_at, d.decision_id))
    overrides = {}
    for (name, idx), v in session.setup.items("program_columns"):
        tk = next((k for k, f in file_of.items() if f == (name, idx)), None)
        if tk:
            overrides[tk] = v
    inherited_progs = list(xw.programs(rows[rk].value("Program") for rk in counted)) if xw else []
    names, proposals, pm, program_of = pl.programs_step(works, counted, [program_decision(d) for d in pdecs] + inherited_progs,
                                                        overrides)
    for d in pdecs:
        if any(dec == program_decision(d) and why == "names_gone" for dec, why in pm.not_applied):
            nla.append(NoLongerApply(d, "names_gone"))
        else:
            applied.add(d.decision_id)

    # Steps 11 and 12: count, balance and confidence.
    outcome_list = [outcomes[k] for k in sorted(outcomes)]
    counts = count(outcome_list, identity, person_of, program_of, len(identity.proposals), len(open_groups),
                   len(pm.unconfirmed), False, pm.not_in_goal2, {rk for rk in counted if pl.dob_valid(rows[rk])})
    if xw is not None:
        counts = dataclasses.replace(counts, matched_from_earlier=xw.matched_from_earlier(
            {identity.master_of_record[rk] for rk in counted}))
        xw.close()
    balance = balance_of(outcome_list, _accounting(load, tables))
    conf = batch_confidence(counts)
    if sink.cancelled():
        raise Cancelled()
    version = (session.results.version + 1) if session.results else 1
    return Results(
        version=version, fingerprints=fps, outcomes=outcomes, rows=rows, works=works, groups=tuple(groups),
        open_groups=open_groups, identity=identity, person_of_record=person_of, file_of_record=file_name_of,
        system_of_record=system_of, program_names=tuple(names), program_proposals=tuple(proposals), program_map=pm,
        program_of_record=program_of, counts=counts, balance=balance, confidence=conf, placements=placement, fills=fills,
        replay=rep, no_longer_apply=tuple(nla), kept=len(applied), lapsed=len(nla),
        practice=backend.name == "reference_sample", release=getattr(backend, "release", ""), backend=backend.name, load=load,
        crosswalk=xw.summary() if xw else None)


class _CrosswalkRead:
    """What the saved crosswalk gave one run (XW-4, XW-5). The store stays open only for the run."""

    def __init__(self, store, batch_id):
        self.store, self.batch_id = store, batch_id
        self.known, self.verdicts, self.keep_saved, self.lapsed = {}, [], set(), 0

    def programs(self, names):
        from wholecount.engine.crosswalk.apply import inherited_programs

        return inherited_programs(self.store, {n for n in names if n})

    def matched_from_earlier(self, masters):
        first = self.store.first_batches(masters)
        return sum(1 for m in masters if m in first and first[m] != self.batch_id)

    def summary(self):
        from wholecount.session.crosswalk import CrosswalkRun

        return CrosswalkRun(self.batch_id, frozenset(self.keep_saved), self.lapsed)

    def close(self):
        self.store.close()


def _lapse(nla, a, b, reviewer, at):
    """A No longer apply entry for a saved decision that new evidence overrides. It names no value (H8)."""
    from wholecount.session.decisions import make

    nla.append(NoLongerApply(make("pair", (), "crosswalk", at, reviewer, person_keys=(a, b)), "dob_now_differs"))


def _crosswalk_read(session, backend, load, by_person, nla):
    """XW-4 and XW-5. None while the crosswalk is off, orphaned, or the run is practice (it's never read then)."""
    from wholecount.engine.crosswalk.apply import inherited_verdicts, load_known
    from wholecount.session import crosswalk

    if not crosswalk.in_use(session, backend.name == "reference_sample"):
        return None
    store = crosswalk.open_store(session)
    xw = _CrosswalkRead(store, crosswalk.batch_id_of(session, load))
    weights = load_settings()["weights"]

    def dob_differs(a, b):
        return "dob_differs" in score_pair(_facts(by_person[a]), _facts(by_person[b]), False, weights).evidence

    known = load_known(store, by_person)
    # A reviewer-made saved link that would come back as an earlier_batch join, but whose dates of birth now differ.
    by_master = {}
    for k, km in known.items():
        by_master.setdefault(km.master_id, []).append(k)
    for ks in by_master.values():
        ks = sorted(ks, key=lambda k: (known[k].linked_at, k))
        for k in ks[1:]:
            if (known[k].how == "reviewer" or known[ks[0]].how == "reviewer") and dob_differs(ks[0], k):
                _lapse(nla, ks[0], k, "", known[k].linked_at)
                xw.keep_saved.add(k)
                xw.lapsed += 1
    xw.known = {k: v for k, v in known.items() if k not in xw.keep_saved}
    lapsed_pairs = {tuple(sorted(n.decision.person_keys)) for n in nla if n.reason == "dob_now_differs"}
    for v in inherited_verdicts(store, by_person):
        if v.verdict == "same" and dob_differs(v.a, v.b):
            if v.pair not in lapsed_pairs:
                _lapse(nla, v.a, v.b, v.reviewer, v.decision_id[3:])
                xw.lapsed += 1
            continue
        xw.verdicts.append(v)
    return xw


def process(session, sink=None):
    """Process: run and swap the results in. A cancel raises Cancelled and leaves the session as it was."""
    results = run(session, sink)
    session.remember(results)
    return results


def recompute_from(session, node=None):
    """Re-run after a decision. Loading is cached by the sources fingerprint, so only later steps do real work."""
    return process(session)


def fast_path(session, sink=None):
    """Stop at Programs while a proposal is open, block on an unmapped required field, else run. No code of its own."""
    results = run(session, sink)
    for w in results.works:
        for b in process_blocks(session.schema(), {w.table.key: w.mapping}):
            raise Blocked(b.table_key, b.field)
    gate = fast_path_gate(results.program_map)
    if isinstance(gate, StopAtPrograms):
        session.remember(results)
        return gate
    session.remember(results)
    return results


def preview_counts(session, program_decisions):
    """Counts with extra program decisions, on a copy: no decision, stale flag or undo entry changes (A-07)."""
    import copy as _copy

    from wholecount.session import decisions as dmod

    shadow = _copy.copy(session)
    shadow.decisions = dmod.DecisionStore(session.decisions.snapshot())
    shadow.results = session.results
    shadow.decisions.add(program_decisions)
    return run(shadow).counts


def causes_for(results):
    """REV-2 with the session's facts: which rows a fill could fix and which have no address at all."""
    from wholecount.engine.review import causes

    no_address = {k for k, r in results.rows.items()
                  if not any(r.value(f).strip() for f in ("Address_1", "Address_2", "City", "State", "Zip"))}
    return causes(list(results.outcomes.values()), results.open_groups, results.replay.routed, set(results.fills), no_address)
