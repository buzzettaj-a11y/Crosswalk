"""The saved crosswalk in the session (SPEC 10.5, M13 XW-1, XW-3, XW-6, XW-7).

It is on exactly when crosswalk.db exists. Turning it on and forgetting it are not on the undo stack, and the window says so.
Both change the identity node's fingerprint, so identity and programs go out of date. A practice run never reads or writes it.
"""
import os
from dataclasses import dataclass

from wholecount.engine.crosswalk.schema import CrosswalkOrphaned
from wholecount.engine.crosswalk.store import CrosswalkLoop, CrosswalkStore
from wholecount.engine.outputs.audit_entry import entry

FORGET_WORD = "forget"
FILE_NAME = "crosswalk.db"


class CrosswalkRefused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def default_path():
    from wholecount.paths import data_dir

    return data_dir() / FILE_NAME


def path_of(session):
    return getattr(session, "crosswalk_path", None)


def state(session):
    """off, on or orphaned."""
    p = path_of(session)
    if p is None or not p.exists():
        return "off"
    try:
        CrosswalkStore.open(p, session.secret.mac).close()
    except (CrosswalkOrphaned, CrosswalkLoop):
        return "orphaned"
    return "on"


def fingerprint(session):
    """The crosswalk's part of the identity node's own inputs (STALE-1): whether the file exists, and its size and change time.
    A commit refreshes the stored fingerprint, so a download never makes the results look out of date (XW-7)."""
    p = path_of(session)
    if p is None or not p.exists():
        return "off"
    st = os.stat(p)
    return f"{st.st_size}:{st.st_mtime_ns}"


def in_use(session, practice):
    return not practice and state(session) == "on"


def open_store(session):
    return CrosswalkStore.open(path_of(session), session.secret.mac)


def summary(session):
    """(since, by, CrosswalkCounts) while on, else None."""
    if state(session) != "on":
        return None
    with open_store(session) as st:
        at, by = st.since()
        return at, by, st.counts()


class TurnOnCrosswalk:
    """Creates crosswalk.db and logs CROSSWALK_ON with the reviewer and time. Not on the undo stack."""

    def __init__(self, reviewer):
        if not (reviewer or "").strip():
            raise CrosswalkRefused("reviewer_missing")
        self.reviewer = reviewer.strip()

    def run(self, session):
        p = path_of(session)
        if p is None:
            raise CrosswalkRefused("no_path")
        if p.exists():
            raise CrosswalkRefused("already_on")
        now = session.now_iso()
        CrosswalkStore.create(p, session.secret.mac, now, self.reviewer).close()
        session.log(entry("CROSSWALK_ON", reviewer=self.reviewer, time_iso=now))


class ForgetCrosswalk:
    """Deletes crosswalk.db after the typed word. A wrong word changes nothing. Not on the undo stack."""

    def __init__(self, typed):
        self.typed = typed or ""

    def run(self, session):
        if self.typed.strip().casefold() != FORGET_WORD:
            return False
        p = path_of(session)
        if p is None or not p.exists():
            return False
        p.unlink()
        session.log(entry("CROSSWALK_FORGET", reviewer=session.reviewer or None, time_iso=session.now_iso()))
        return True


def batch_id_of(session, load):
    """B- plus 10 hex of mac(b"batch|" + the sorted source fingerprints), so the same files make the same batch (XW-6)."""
    fps = sorted(o.fingerprint for o in (load.files if load else ()) if o.status == "ok" and o.fingerprint)
    return "B-" + session.secret.mac(b"batch|" + "\x1f".join(fps).encode("ascii")).hex()[:10]


@dataclass(frozen=True)
class CrosswalkRun:
    """What a run took from the crosswalk: the batch ID, the keys whose saved link lapsed, and how many saved items lapsed."""
    batch_id: str
    keep_saved: frozenset
    lapsed: int


def commit_view(session):
    """The CommitView of the current results: counted rows' person keys, how each joined its person, and this batch's own
    pair and program decisions that still apply."""
    from wholecount.engine.crosswalk.apply import CommitView

    r = session.results
    idt = r.identity
    counted = {rk for rk, o in r.outcomes.items() if o.counted}
    pks = {r.person_of_record[rk] for rk in counted if rk in r.person_of_record}
    rank = {"derived": 0, "same_system_id": 1, "four_exact_facts": 2, "reviewer": 3}
    how = {pk: "derived" for pk in pks}

    def mark(pk, h):
        if pk in how and rank[h] > rank[how[pk]]:
            how[pk] = h
    for j in idt.auto_joins:
        if j.reason == "same_system_id":
            a, b = (r.person_of_record.get(k) for k in j.pair)
        else:
            a, b = j.pair
        h = "reviewer" if j.reason == "earlier_batch" else j.reason
        mark(a, h)
        mark(b, h)
    lapsed = {n.decision.decision_id for n in r.no_longer_apply}
    verdicts = []
    for d in session.decisions.of_kind("pair"):
        if d.decision_id in lapsed or len(d.person_keys) != 2:
            continue
        a, b = d.person_keys
        if a in pks and b in pks:
            verdicts.append((a, b, d.get("verdict"), d.reviewer, d.second_reviewer, d.made_at))
            if d.get("verdict") == "same":
                mark(a, "reviewer")
                mark(b, "reviewer")
    programs = [(d.get("program_kind"), d.get("label"), tuple(d.all("program")), d.reviewer, d.made_at)
                for d in session.decisions.of_kind("program") if d.decision_id not in lapsed]
    return CommitView(r.crosswalk.batch_id, {pk: idt.master_of[pk] for pk in pks}, how, tuple(idt.merged),
                      tuple(sorted(verdicts)), tuple(programs), r.crosswalk.keep_saved)


def commit_after_download(session):
    """XW-6: once, after a download succeeds, and never in a practice run. Returns None when nothing was to be written, the
    CommitCounts when it was written, or "failed" when it rolled back. The stored fingerprint is refreshed after (XW-7)."""
    from wholecount.engine.crosswalk.apply import commit

    r = session.results
    if r is None or r.practice or r.crosswalk is None or state(session) != "on":
        return None
    try:
        with open_store(session) as st:
            counts = commit(st, commit_view(session), session.reviewer or "", session.now_iso())
    except Exception:  # noqa: BLE001  any failure rolls back; the receipt says the crosswalk wasn't updated
        return "failed"
    session.log(entry("CROSSWALK_UPDATED", count=[counts.people, counts.person_keys, counts.pair_verdicts,
                                                   counts.program_groups, counts.merged],
                      reviewer=session.reviewer or None, time_iso=session.now_iso()))
    r.fingerprints = session.live_fingerprints()
    return counts
