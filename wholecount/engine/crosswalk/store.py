"""CrosswalkStore: every SQL statement for crosswalk.db lives here (M13 XW-2 to XW-6)."""
import hashlib
from dataclasses import dataclass

from wholecount.engine.crosswalk.schema import create_db, open_db

MAX_HOPS = 20
SEP = "\x1f"


class CrosswalkLoop(Exception):
    """merged_into points in a circle or runs past 20 hops. The file is damaged, so nothing in it is trusted."""


@dataclass(frozen=True)
class SavedKey:
    person_key: str
    master_id: str        # the final master, after merged_into
    created_at: str       # when that master was made
    how: str
    linked_at: str        # when this key was linked


@dataclass(frozen=True)
class SavedVerdict:
    key_a: str
    key_b: str
    verdict: str
    decided_by: str
    second_reviewer: str | None
    decided_at: str


@dataclass(frozen=True)
class SavedProgramGroup:
    group_id: str
    kind: str
    label: str | None
    members: tuple
    decided_by: str
    decided_at: str


@dataclass(frozen=True)
class CrosswalkCounts:
    people: int
    person_keys: int
    pair_verdicts: int
    program_groups: int
    merged: int


def program_group_id(members):
    return "P-" + hashlib.sha256(SEP.join(sorted(members)).encode("utf-8")).hexdigest()[:10]


class CrosswalkStore:
    def __init__(self, con):
        self.con = con

    @classmethod
    def create(cls, path, mac, created_at, created_by):
        return cls(create_db(path, mac, created_at, created_by))

    @classmethod
    def open(cls, path, mac):
        return cls(open_db(path, mac))

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # Reading

    def meta(self, key):
        row = self.con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def final_master(self, master_id):
        seen = [master_id]
        while True:
            row = self.con.execute("SELECT new_master FROM merged_into WHERE old_master = ?", (seen[-1],)).fetchone()
            if row is None:
                return seen[-1]
            if row[0] in seen or len(seen) > MAX_HOPS:
                raise CrosswalkLoop()
            seen.append(row[0])

    def keys(self, person_keys):
        out = {}
        for pk in sorted(set(person_keys)):
            row = self.con.execute("SELECT master_id, how, decided_at FROM person_key WHERE person_key = ?", (pk,)).fetchone()
            if row is None:
                continue
            final = self.final_master(row[0])
            created = self.con.execute("SELECT created_at FROM person WHERE master_id = ?", (final,)).fetchone()
            out[pk] = SavedKey(pk, final, created[0] if created else row[2], row[1], row[2])
        return out

    def first_batches(self, master_ids):
        out = {}
        for m in sorted(set(master_ids)):
            row = self.con.execute("SELECT first_batch FROM person WHERE master_id = ?", (m,)).fetchone()
            if row is not None:
                out[m] = row[0]
        return out

    def verdicts_among(self, person_keys):
        keys = set(person_keys)
        rows = self.con.execute("SELECT key_a, key_b, verdict, decided_by, second_reviewer, decided_at FROM pair_verdict "
                                "ORDER BY key_a, key_b").fetchall()
        return [SavedVerdict(*r) for r in rows if r[0] in keys and r[1] in keys]

    def program_groups(self):
        rows = self.con.execute("SELECT group_id, kind, label, members, decided_by, decided_at FROM program_group "
                                "ORDER BY group_id").fetchall()
        return [SavedProgramGroup(r[0], r[1], r[2], tuple(r[3].split(SEP)) if r[3] else (), r[4], r[5]) for r in rows]

    def counts(self):
        one = lambda sql: self.con.execute(sql).fetchone()[0]  # noqa: E731
        return CrosswalkCounts(one("SELECT COUNT(*) FROM person"), one("SELECT COUNT(*) FROM person_key"),
                               one("SELECT COUNT(*) FROM pair_verdict"), one("SELECT COUNT(*) FROM program_group"),
                               one("SELECT COUNT(*) FROM merged_into"))

    def since(self):
        return self.meta("created_at"), self.meta("created_by")

    # Writing, in one transaction

    def write(self, plan):
        """plan: a CommitPlan. All or nothing: any error rolls back and leaves the file as it was."""
        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            for m in plan.new_people:
                con.execute("INSERT OR IGNORE INTO person(master_id, created_at, created_by, first_batch) VALUES (?, ?, ?, ?)",
                            (m, plan.time, plan.reviewer, plan.batch_id))
            for old, new in plan.merged:
                con.execute("INSERT OR REPLACE INTO merged_into(old_master, new_master, merged_at) VALUES (?, ?, ?)",
                            (old, new, plan.time))
            for pk, master, how in plan.keys:
                con.execute("INSERT INTO person_key(person_key, master_id, how, decided_by, decided_at) VALUES (?, ?, ?, ?, ?) "
                            "ON CONFLICT(person_key) DO UPDATE SET master_id = excluded.master_id, how = excluded.how, "
                            "decided_by = excluded.decided_by, decided_at = excluded.decided_at",
                            (pk, master, how, plan.reviewer, plan.time))
            for a, b, verdict, by, second, at in plan.verdicts:
                con.execute("INSERT OR REPLACE INTO pair_verdict(key_a, key_b, verdict, decided_by, second_reviewer, decided_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)", (min(a, b), max(a, b), verdict, by, second, at))
            for kind, label, members, by, at in plan.programs:
                con.execute("INSERT OR REPLACE INTO program_group(group_id, kind, label, members, decided_by, decided_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)", (program_group_id(members), kind, label, SEP.join(sorted(members)),
                                                          by, at))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
