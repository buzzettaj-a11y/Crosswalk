"""Standard library modules later milestones need stay allowed under the guard: sqlite3 (M13) and hashlib.scrypt, hmac, secrets, getpass (M01, M13)."""
from tests.support.guarded import run_guarded
from tools.offline_rules import ALLOWED_STDLIB, FORBIDDEN_MODULES
from wholecount.guard.offline_guard import DENY_MODULES


def test_sqlite3_and_scrypt_work_under_the_guard():
    r = run_guarded("""
        import sqlite3, hashlib, hmac, secrets, getpass
        con = sqlite3.connect(':memory:')
        con.execute('create table t (k text, v integer)')
        con.execute('insert into t values (?, ?)', ('a', 1))
        out['select'] = con.execute('select k, v from t').fetchall()
        con.close()
        key = hashlib.scrypt(b'pw', salt=bytes(16), n=2**15, r=8, p=1, maxmem=2**26, dklen=32)
        out['scrypt_len'] = len(key)
        out['hmac'] = len(hmac.new(key, b'x', 'sha256').digest())
        out['secrets'] = len(secrets.token_bytes(16))
        out['getpass'] = callable(getpass.getuser)
        out['violations'] = violations
    """, install="guard.install_for_app()")
    assert r == {"select": [["a", 1]], "scrypt_len": 32, "hmac": 32, "secrets": 16, "getpass": True, "violations": []}, r


def test_allowed_stdlib_is_in_neither_deny_list():
    assert set(ALLOWED_STDLIB) == {"sqlite3", "hashlib", "hmac", "secrets", "getpass"}
    for name in ALLOWED_STDLIB:
        assert name not in FORBIDDEN_MODULES, name
        assert name not in DENY_MODULES, name
