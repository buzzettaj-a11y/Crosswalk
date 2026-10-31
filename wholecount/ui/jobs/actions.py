"""The jobs stages 01 to 05 start (SPEC 11.6.2): adding files, Process and the program preview.

run(sink) works on the worker and only reads. apply(session, result) runs on the main thread inside one command, so a
cancelled job leaves the session as it was and one Undo takes back a finished one.
"""
import pathlib

from wholecount.session.commands import AddSources


class AddFilesJob:
    """Reading files, Finding tables. The load result seeds the session's load cache, so Process doesn't read again."""

    action_id = "add_files"

    def __init__(self, session, paths, ui=None):
        from wholecount.ui.jobs.steps import steps_of

        self.ui = ui if ui is not None else {}

        self.steps = steps_of("add_files")
        self.secret = session.secret
        self.keep = session.keep_sensitive
        known = set(map(str, session.setup.paths()))
        self.new = [str(p) for p in paths if str(p) not in known]
        self.all = [*map(str, session.setup.paths()), *self.new]
        self.cmd = AddSources(self.new)

    def run(self, sink):
        from wholecount.session.loader import load_files

        return load_files([pathlib.Path(p) for p in self.all], sink, self.secret, keep=self.keep)

    def apply(self, session, load):
        from wholecount.session.frame import corrections_files

        corrections = corrections_files(load)
        if corrections:
            # Recognized as corrections, never as a source. Process reads the real sources itself.
            self.cmd = AddSources([p for p in self.new if pathlib.Path(p).name not in corrections])
            self.ui["corrections_files"] = tuple(self.ui.get("corrections_files", ())) + tuple(corrections)
        self.cmd.apply(session)
        if not corrections:
            session._load_cache = (session.setup.stable("sources") + repr(sorted(session.keep_sensitive)), load)
        return None

    def undo(self, session, token):
        self.cmd.undo(session)


class ProcessJob:
    """Process: the seven steps over every included table. The old Results come back on Undo."""

    action_id = "process"

    def __init__(self, session):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("process")
        self.session = session

    def run(self, sink):
        from wholecount.session.runner import run

        return run(self.session, sink)

    def apply(self, session, results):
        before = (session.results, list(session.recent))
        session.remember(results)
        return before

    def undo(self, session, token):
        session.results, session.recent = token[0], token[1]


class PreviewJob:
    """Preview the counts (Programs). It never decides anything and is not on the undo stack (A-07)."""

    action_id = "preview"
    undoable = False

    def __init__(self, session, on_done):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("preview")
        self.session = session
        self.on_done = on_done

    def run(self, sink):
        from wholecount.session.runner import preview_counts

        return preview_counts(self.session, [])

    def apply(self, session, counts):
        self.on_done(counts)


class ResumeJob:
    """Resume: read the saved progress, then re-apply its set-up and decisions to the files added again (SPEC 10.2).
    Not on the undo stack: it starts a batch."""

    action_id = "resume"
    undoable = False

    def __init__(self, store, entry, paths, on_done):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("resume")
        self.store, self.entry, self.paths, self.on_done = store, entry, list(paths), on_done

    def run(self, sink):
        return self.store.load(self.entry["path"])

    def apply(self, session, saved):
        from wholecount.session.resume import resume

        self.on_done(resume(session, saved, self.paths))


class LookUpJob:
    """Look up all {n}: gathers what would be filled. Nothing is dispatched until Apply in the fill preview."""

    action_id = "look_up"
    undoable = False

    def __init__(self, session, cause_id, record_keys, on_done):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("look_up")
        self.session, self.cause_id, self.keys, self.on_done = session, cause_id, tuple(record_keys), on_done

    def run(self, sink):
        from wholecount.session.progress import ProgressMessage, Step, Unit

        sink.begin(Step.LOOKING_UP_ADDRESSES, len(self.keys), Unit.ADDRESSES)
        found = sum(1 for k in self.keys if k in self.session.results.fills)
        sink.advance(len(self.keys), ProgressMessage("progress.found.demo", {"n": len(self.keys)}))
        sink.end(ProgressMessage("progress.found.demo", {"n": found}))
        return self.keys

    def apply(self, session, keys):
        self.on_done(self.cause_id, keys)


class CorrectionsJob:
    """Applying a corrections file: read it, check signatures and originals, re-apply decisions (SPEC 8.6, 11.6.2)."""

    action_id = "corrections"

    def __init__(self, session, path, on_done):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("corrections")
        self.session, self.path, self.on_done = session, path, on_done
        self.cmd = None

    def run(self, sink):
        from wholecount.session.corrections_view import read_corrections_file
        from wholecount.session.progress import ProgressMessage, Step, Unit

        sink.begin(Step.READING_CORRECTIONS, 1, Unit.ROWS)
        got = read_corrections_file(self.session, self.path)
        sink.end(ProgressMessage("progress.found.demo", {"n": got.rows_read}))
        sink.begin(Step.CHECKING_SIGNATURES, got.rows_read, Unit.CHECKS)
        sink.end(ProgressMessage("progress.found.demo", {"n": len(got.accepted)}))
        return got

    def apply(self, session, got):
        from wholecount.session.commands import ApplyCorrections

        before = {c.record_key for c in got.accepted if session.results.outcomes[c.record_key].counted}
        if got.accepted:
            self.cmd = ApplyCorrections(got.accepted, got.fingerprint, got.file_name)
            self.cmd.apply(session)
            session.log(self.cmd.audit_entry())
            from wholecount.session.runner import recompute_from

            recompute_from(session)
        now = {c.record_key for c in got.accepted if session.results.outcomes[c.record_key].counted}
        self.on_done(got, len(now - before) + len(before))
        return None

    def undo(self, session, token):
        if self.cmd is not None:
            self.cmd.undo(session)
            from wholecount.session.runner import recompute_from

            recompute_from(session)


class DownloadJob:
    """Download: writes every file under a temporary name, then renames (M09). The audit entry is logged once, on apply."""

    action_id = "download"
    undoable = False

    def __init__(self, session, folder, settings, on_done, environ=None):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("download")
        self.session, self.folder, self.settings, self.on_done = session, folder, settings, on_done
        self.environ = environ

    def run(self, sink):
        from wholecount.session.frame import planned_file_count, write_download, write_reason
        from wholecount.session.progress import ProgressMessage, Step, Unit

        n = planned_file_count(self.session, self.settings)
        sink.begin(Step.WRITING_FILES, n, Unit.FILES)
        if sink.cancelled():
            return ("cancelled", None)
        try:
            receipt = write_download(self.session, self.folder, self.settings, self.environ)
        except OSError as exc:
            return ("failed", write_reason(exc))
        sink.advance(n, ProgressMessage("progress.found.demo", {"n": n}))
        sink.end(ProgressMessage("progress.found.demo", {"n": len(receipt.files)}))
        return ("done", receipt)

    def apply(self, session, result):
        from wholecount.session.frame import log_download

        kind, value = result
        if kind == "done":
            log_download(session, value)
        self.on_done(kind, value)


class BackupJob:
    """Protecting the backup (SPEC 11.6.2): scrypt can pass 300 ms, so the file is written on the worker. Not on the undo
    stack. The passphrase lives only inside the BackupSecret, which forgets it once the file is written."""

    action_id = "backup"
    undoable = False

    def __init__(self, session, backup, on_done):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("backup")
        self.session, self.backup, self.on_done = session, backup, on_done

    def run(self, sink):
        from wholecount.session.progress import ProgressMessage, Step, Unit

        sink.begin(Step.PROTECTING_BACKUP, 1, Unit.FILES)
        n = self.backup.run(self.session)
        sink.end(ProgressMessage("progress.found.demo", {"n": 1}))
        return n

    def apply(self, session, n):
        self.on_done(n)


class CalibrateJob:
    """Matching people across files, Drawing pairs (SPEC 11.6.2). Draws the sample; changes nothing in the session."""

    action_id = "calibrate"
    undoable = False

    def __init__(self, session, per_band, on_done, protect=None, unprotect=None):
        from wholecount.ui.jobs.steps import steps_of

        self.steps = steps_of("calibrate")
        self.session, self.per_band, self.on_done = session, per_band, on_done
        self.protect, self.unprotect = protect, unprotect

    def run(self, sink):
        from wholecount.session.calibration import CalibrationSession
        from wholecount.session.progress import ProgressMessage, Step, Unit

        sink.begin(Step.MATCHING_PEOPLE, 1, Unit.ROWS)
        sink.end(ProgressMessage("progress.found.demo", {"n": len(self.session.results.person_of_record)}))
        sink.begin(Step.DRAWING_PAIRS, 1, Unit.PAIRS)
        cal = CalibrationSession.draw(self.session, self.per_band, self.protect, self.unprotect)
        sink.end(ProgressMessage("progress.found.demo", {"n": len(cal.pairs)}))
        return cal

    def apply(self, session, cal):
        self.on_done(cal)
