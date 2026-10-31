"""crosswalk.db's tables (M13 XW-2). sqlite3 from the standard library, journal_mode=DELETE so no -wal or -shm file is ever
left beside it (H9), and user_version 1. The file holds no name, address, Client_ID value or date of birth: keys are 64-hex
person keys, master IDs are M- plus 10 hex, and its dates are the times of decisions."""
import sqlite3

FORMAT = "1"
USER_VERSION = 1
HOWS = ("derived", "same_system_id", "four_exact_facts", "reviewer")
SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE person(master_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, created_by TEXT NOT NULL, first_batch TEXT NOT NULL);
CREATE TABLE person_key(person_key TEXT PRIMARY KEY, master_id TEXT NOT NULL REFERENCES person,
  how TEXT NOT NULL CHECK(how IN ('derived','same_system_id','four_exact_facts','reviewer')), decided_by TEXT NOT NULL,
  decided_at TEXT NOT NULL);
CREATE TABLE pair_verdict(key_a TEXT NOT NULL, key_b TEXT NOT NULL, verdict TEXT NOT NULL CHECK(verdict IN ('same','different')),
  decided_by TEXT NOT NULL, second_reviewer TEXT, decided_at TEXT NOT NULL, PRIMARY KEY(key_a, key_b), CHECK(key_a < key_b));
CREATE TABLE program_group(group_id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT, members TEXT NOT NULL,
  decided_by TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE merged_into(old_master TEXT PRIMARY KEY, new_master TEXT NOT NULL, merged_at TEXT NOT NULL);
"""


class CrosswalkOrphaned(Exception):
    """The file was made with a different install secret, so its keys mean nothing here. It's ignored and never written."""


def secret_check(mac):
    return mac(b"crosswalk|check").hex()[:16]


def _connect(path):
    con = sqlite3.connect(str(path), isolation_level=None)
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def create_db(path, mac, created_at, created_by):
    """A new, empty crosswalk. Refuses to overwrite an existing file."""
    import pathlib

    path = pathlib.Path(path)
    if path.exists():
        raise FileExistsError(path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = _connect(path)
    try:
        con.execute("BEGIN")
        for stmt in [s for s in SCHEMA.split(";") if s.strip()]:
            con.execute(stmt)
        con.executemany("INSERT INTO meta(key, value) VALUES (?, ?)",
                        [("format", FORMAT), ("created_at", created_at), ("created_by", created_by),
                         ("secret_check", secret_check(mac))])
        con.execute(f"PRAGMA user_version = {USER_VERSION}")
        con.execute("COMMIT")
    except Exception:
        con.close()
        path.unlink(missing_ok=True)
        raise
    return con


def open_db(path, mac):
    """An open connection, after checking the file was made with this install secret (XW-3)."""
    con = _connect(path)
    try:
        row = con.execute("SELECT value FROM meta WHERE key = 'secret_check'").fetchone()
    except sqlite3.DatabaseError:
        con.close()
        raise CrosswalkOrphaned() from None
    if row is None or row[0] != secret_check(mac):
        con.close()
        raise CrosswalkOrphaned()
    return con
