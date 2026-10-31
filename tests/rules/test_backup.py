"""Install secret backup and restore (SPEC 5.1, M13 BAK-1 to BAK-4)."""
import ast
import unicodedata

import pytest

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from wholecount.engine.secretbackup import BLOB_BYTES, BackupError, make_backup, read_backup
from wholecount.session import keys
from wholecount.session.backup import BackupRefused, BackupSecret, RestoreSecret
from wholecount.session.secret_store import FileSecretStore, InstallSecret

PASS = "correct horse battery staple"
SALT = bytes(range(16))
BLOB = ("57434231000102030405060708090a0b0c0d0e0f819956c362b0ba0d33e90b391c32960f1e927297476698fb8341002bde214ca8"
        "fc435e355253a2ec4c73060ea9261179f015affbf30b6c477b3938d53fbba454")


def test_BAK_1_format():
    blob = make_backup(TEST_SECRET, PASS)
    assert len(blob) == BLOB_BYTES == 84 and blob[:4] == b"WCB1"
    assert TEST_SECRET not in blob


def test_BAK_2_known_answer():
    blob = make_backup(TEST_SECRET, PASS, SALT)
    assert blob.hex() == BLOB
    assert blob[20:52].hex() == "819956c362b0ba0d33e90b391c32960f1e927297476698fb8341002bde214ca8"
    assert blob[52:].hex() == "fc435e355253a2ec4c73060ea9261179f015affbf30b6c477b3938d53fbba454"


def test_BAK_3_round_trip_and_random_salts():
    a, b = make_backup(TEST_SECRET, PASS), make_backup(TEST_SECRET, PASS)
    assert a != b and read_backup(a, PASS) == TEST_SECRET == read_backup(b, PASS)


@pytest.mark.parametrize("where", [0, 10, 30, 70])
def test_BAK_3_any_changed_byte_is_refused(where):
    blob = bytearray(bytes.fromhex(BLOB))
    blob[where] ^= 1
    with pytest.raises(BackupError) as e:
        read_backup(bytes(blob), PASS)
    assert e.value.code == ("not_a_backup" if where < 4 else "wrong_passphrase_or_damaged")


def test_BAK_3_wrong_passphrase_short_and_long():
    blob = bytes.fromhex(BLOB)
    with pytest.raises(BackupError) as e:
        read_backup(blob, PASS + "x")
    assert e.value.code == "wrong_passphrase_or_damaged"
    for bad in (blob[:-1], blob + b"\x00"):
        with pytest.raises(BackupError) as e:
            read_backup(bad, PASS)
        assert e.value.code == "not_a_backup"


def test_BAK_3_nfkc():
    composed, decomposed = "café au lait daily", "café au lait daily"
    assert composed != decomposed and unicodedata.normalize("NFKC", decomposed) == composed
    assert read_backup(make_backup(TEST_SECRET, composed), decomposed) == TEST_SECRET


def test_BAK_4_refusals(tmp_path):
    for args, code in (((PASS, PASS + "!", tmp_path / "b"), "passphrase_mismatch"), (("", "", tmp_path / "b"), "passphrase_empty"),
                       (("eleven char", "eleven char", tmp_path / "b"), "passphrase_short")):
        with pytest.raises(BackupRefused) as e:
            BackupSecret(*args)
        assert e.value.code == code
    assert "correct" not in repr(BackupSecret(PASS, PASS, tmp_path / "b"))


def test_BAK_4_backup_restore_and_the_record_key_known_answer(tmp_path):
    s = r_fixture.session(tmp_path / "w")
    store = FileSecretStore(tmp_path / "key")
    store.save(TEST_SECRET)
    path = tmp_path / "secret.wcb"
    assert BackupSecret(PASS, PASS, path).run(s) == 84
    assert path.read_bytes() != TEST_SECRET and TEST_SECRET not in path.read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["key", "secret.wcb", "w"]
    # Restoring the same secret changes nothing.
    assert RestoreSecret(path, PASS).run(s, store).same
    # Over a different secret it needs the typed word.
    s.secret = InstallSecret(OTHER_SECRET)
    store.save(OTHER_SECRET)
    assert RestoreSecret(path, PASS, "yes").run(s, store).needs_word and store.load() == OTHER_SECRET
    with pytest.raises(BackupError):
        RestoreSecret(path, "not the passphrase", "replace").run(s, store)
    assert RestoreSecret(path, PASS, "replace").run(s, store).restored
    assert store.load() == TEST_SECRET and s.secret.same_as(TEST_SECRET)
    tk = "clinic_export_csv :: data :: 3380a5d7"
    row = ["Ada Sample", "125 Worth St Apt 4B New York NY 10013"]
    assert keys.record_keys(s.secret, tk, [row])[0] == "7533705e667f8cf12288"
    codes = [e.code for _, e in s.audit_log]
    assert codes.count("SECRET_BACKUP") == 1 and codes.count("SECRET_RESTORE") == 1
    text = repr(s.audit_log)
    assert PASS not in text and TEST_SECRET.hex() not in text and OTHER_SECRET.hex() not in text


def test_BAK_4_a_restore_marks_everything_stale(tmp_path):
    from tests.support.session import base

    s = base(tmp_path / "w")
    store = FileSecretStore(tmp_path / "key")
    path = tmp_path / "b.wcb"
    path.write_bytes(make_backup(OTHER_SECRET, PASS))
    RestoreSecret(path, PASS, "replace").run(s, store)
    assert "sources" in s.stale


def test_BAK_static_standard_library_only():
    src = (ROOT / "wholecount" / "engine" / "secretbackup.py").read_text(encoding="utf-8")
    assert "compare_digest" in src and "hashlib.scrypt" in src and "shake_256" in src
    mods = {a.name.split(".")[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert mods <= {"hashlib", "hmac", "secrets", "unicodedata"}


def test_backup_demo_prints_counts_only(tmp_path):
    """In a subprocess, because importing wholecount.dev installs the guard."""
    import subprocess
    import sys

    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "backup-demo"], cwd=tmp_path, capture_output=True, text=True,
                       timeout=120, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
    assert p.returncode == 0, p.stderr
    assert p.stdout.split("\n")[:6] == ["backup_bytes 84", "known_answer_matches 1", "restore_ok 1",
                                        "wrong_passphrase_refused 1", "one_changed_byte_refused 1", "files_written 0"]
    assert list(tmp_path.iterdir()) == []
