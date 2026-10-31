"""Loading files into tables (P-READ, SPEC 5.1). Each file is read on its own, so a bad file never blocks the others (A-13).

Per file: read, find tables, compute keys, drop sensitive columns, then release the grids. Only readable files take a letter,
in the order added, and the letter is display only.
"""
from dataclasses import dataclass, field, replace

from wholecount.engine.letters import letter_for_index
from wholecount.engine.progress import ProgressMessage, SourceRef, Step, Unit
from wholecount.engine.read.accounting import FileAccounting, account_grid
from wholecount.engine.read.model import UnreadableFile
from wholecount.engine.read.reader import read_path
from wholecount.engine.read.sensitive import drop_sensitive
from wholecount.engine.read.tables import find_tables
from wholecount.session import keys


class Cancelled(Exception):
    """The operator cancelled. Loading is pure, so nothing changed."""


@dataclass
class FileOutcome:
    name: str
    status: str                       # ok, unreadable or duplicate_file
    reason_id: str | None = None
    fingerprint: str | None = None
    letter: str | None = None
    file_key: str | None = None
    table_count: int = 0
    accounting: FileAccounting = field(default_factory=FileAccounting)
    read_file: object = None          # the ReadFile, with its grids released


@dataclass
class LoadResult:
    files: list
    tables: list

    def counts(self):
        return {s: sum(1 for f in self.files if f.status == s) for s in ("ok", "unreadable", "duplicate_file")}


def table_signature(table):
    if table.header_is_virtual or table.header_row:
        return keys.header_signature(table.raw_headers)
    return keys.header_signature(table.headers)


def key_tables(secret, file_key, tables):
    """Set each table's key and its rows' record keys. Two tables with one key get #2, #3 in discovery order."""
    used = {}
    out = []
    for t in tables:
        sig = table_signature(t)
        base = (t.sheet, sig)
        used[base] = used.get(base, 0) + 1
        k = keys.table_key(file_key, t.sheet, sig, used[base])
        out.append(replace(t, key=k, record_keys=keys.record_keys(secret, k, t.rows)))
    return out


def _check_cancel(sink):
    if sink.cancelled():
        raise Cancelled()


def load_files(paths, sink, secret, keep=frozenset()):
    sink.begin(Step.READING_FILES, len(paths), Unit.FILES)
    reads = []
    for p in paths:
        _check_cancel(sink)
        try:
            reads.append((p, read_path(p), None))
        except UnreadableFile as e:
            reads.append((p, None, e.reason_id))
        sink.advance(1, ProgressMessage("progress.file_count", {"done": len(reads), "total": len(paths)}))
    readable = [(p, rf) for p, rf, _ in reads if rf is not None]
    fkeys = iter(keys.file_keys([(rf.name, rf.fingerprint) for _, rf in readable]))
    outcomes, letter_i = [], 0
    for p, rf, reason in reads:
        if rf is None:
            outcomes.append(FileOutcome(p.name, "unreadable", reason_id=reason))
            continue
        fk = next(fkeys)
        if fk is None:
            outcomes.append(FileOutcome(rf.name, "duplicate_file", reason_id="duplicate_file", fingerprint=rf.fingerprint))
            continue
        outcomes.append(FileOutcome(rf.name, "ok", fingerprint=rf.fingerprint, letter=letter_for_index(letter_i), file_key=fk,
                                    read_file=rf))
        letter_i += 1
    ok = sum(1 for o in outcomes if o.status == "ok")
    sink.end(ProgressMessage("progress.found.reading_files", {"read": ok, "unreadable": len(outcomes) - ok}))

    sink.begin(Step.FINDING_TABLES, ok, Unit.FILES)
    all_tables = []
    for o in outcomes:
        if o.status != "ok":
            continue
        _check_cancel(sink)
        rf = o.read_file
        file_tables = []
        for grid in rf.grids:
            gt = find_tables(grid)
            o.accounting.add(account_grid(grid, gt.tables, gt.non_table_blocks))
            file_tables.extend(gt.tables)
        file_tables = key_tables(secret, o.file_key, file_tables)
        for t in file_tables:
            t.letter = o.letter
            drop_sensitive(t, keep)
        rf.grids = []
        o.table_count = len(file_tables)
        all_tables.extend(file_tables)
        sink.advance(1, ProgressMessage("progress.finding_tables_in", {"source": SourceRef(o.letter, o.name)}))
    sink.end(ProgressMessage("progress.found.finding_tables",
                             {"tables": len(all_tables), "included": sum(1 for t in all_tables if t.included)}))
    return LoadResult(outcomes, all_tables)
