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
