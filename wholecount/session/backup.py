"""Backing up and restoring the install secret (SPEC 5.1, 11.6.2, M13 BAK-4).

Neither is a command on the undo stack: one writes a file the operator chose, the other replaces the secret in the store.
The audit gets SECRET_BACKUP or SECRET_RESTORE with the reviewer and time and nothing else. The passphrase and the secret
never reach a log, a message or a repr.
"""
import os
import pathlib

from wholecount.engine.outputs.audit_entry import entry
from wholecount.engine.secretbackup import BackupError, read_backup
from wholecount.settings.loader import load

REPLACE_WORD = "replace"


class BackupRefused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def passphrase_min():
    return int(load("privacy")["backup_passphrase_min"])


class BackupSecret:
    """BackupSecret(passphrase, again, path). Checks happen when it's made, so a refused one never starts a job."""

    def __init__(self, passphrase, again, path):
        if passphrase != again:
            raise BackupRefused("passphrase_mismatch")
        if not passphrase or not passphrase.strip():
            raise BackupRefused("passphrase_empty")
        if len(passphrase) < passphrase_min():
            raise BackupRefused("passphrase_short")
        self._passphrase = passphrase
        self.path = pathlib.Path(path)

    def __repr__(self):
        return "BackupSecret(hidden)"

    def folder_warning(self, environ=None):
        """M09's synced-folder check on the chosen folder: onedrive, dropbox, google_drive, box, network or None."""
        from wholecount.engine.outputs.folders import folder_warning

        return folder_warning(str(self.path.parent), environ if environ is not None else os.environ)

    def run(self, session, salt=None):
        """Writes the file (the slow part is scrypt, so the window runs this in a job) and logs SECRET_BACKUP."""
        blob = session.secret.backup(self._passphrase, salt)
        self._passphrase = None
        tmp = self.path.with_name("." + self.path.name + ".part")
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, self.path)
        session.log(entry("SECRET_BACKUP", reviewer=session.reviewer or None, time_iso=session.now_iso()))
        return len(blob)


class RestoreResult:
    __slots__ = ("same", "needs_word", "restored")

    def __init__(self, same=False, needs_word=False, restored=False):
        self.same, self.needs_word, self.restored = same, needs_word, restored


class RestoreSecret:
    """RestoreSecret(path, passphrase, typed). Equal to the current secret: nothing changes. Different: only with the
    typed word, then the store saves it and the session's keys change, so every result is out of date."""

    def __init__(self, path, passphrase, typed=""):
        self.path = pathlib.Path(path)
        self._passphrase = passphrase
        self.typed = typed

    def __repr__(self):
        return "RestoreSecret(hidden)"

    def run(self, session, store):
        from wholecount.session.secret_store import InstallSecret

        try:
            raw = read_backup(self.path.read_bytes(), self._passphrase)
        except OSError:
            raise BackupError("not_a_backup") from None
        finally:
            self._passphrase = None
        if session.secret.same_as(raw):
            return RestoreResult(same=True)
        if self.typed.strip().casefold() != REPLACE_WORD:
            return RestoreResult(needs_word=True)
        store.save(raw)
        session.secret = InstallSecret(raw)
        session.log(entry("SECRET_RESTORE", reviewer=session.reviewer or None, time_iso=session.now_iso()))
        return RestoreResult(restored=True)
