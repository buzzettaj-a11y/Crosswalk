"""Developer commands: `python -m wholecount.dev <command>`. Output is counts only (H8).

Every line goes through emit(), which takes a label from the closed CountLabel enum and an int. No command prints a string,
except `check --why`, which prints the names of denied guard events. `check` opens no client file, so those names carry no client value.
"""
from wholecount.guard import install_for_app

_violations = install_for_app()

import enum  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCOPE_RE = re.compile(r"[A-Z]{1,3}(\.[0-9]{1,3})?")


class CountLabel(enum.Enum):
    PINS_RUNTIME = "pins_runtime"
    PINS_DEV = "pins_dev"
    APPROVED_DISTRIBUTIONS = "approved_distributions"
    CLAIMS_IN_REGISTRY = "claims_in_registry"
    AUDIT_IDS_LISTED = "audit_ids_listed"
    MODULES_IMPORTED_UNDER_GUARD = "modules_imported_under_guard"
    GUARD_VIOLATIONS = "guard_violations"
    # read
    TABLES_FOUND = "tables_found"
    TABLES_INCLUDED = "tables_included"
    ROWS_INCLUDED = "rows_included"
    ROWS_EXCLUDED = "rows_excluded"
    ROWS_NON_TABLE = "rows_non_table"
    ROWS_HEADER = "rows_header"
    ROWS_ABOVE_HEADER = "rows_above_header"
    ROWS_SHARED = "rows_shared"
    NON_EMPTY_ROWS = "non_empty_rows"
    BALANCED = "balanced"
    CONTINUATION_BLOCKS = "continuation_blocks"
    SENSITIVE_COLUMNS_DROPPED = "sensitive_columns_dropped"
    SENSITIVE_COLUMNS_BY_VALUES = "sensitive_columns_by_values"
    READ_AS_WINDOWS_TEXT = "read_as_windows_text"
    INVISIBLE_CHARACTERS_REMOVED = "invisible_characters_removed"
    FILES_READ = "files_read"
    FILES_UNREADABLE = "files_unreadable"
    FILES_DUPLICATE = "files_duplicate"
    # secret
    INSTALL_SECRET_CREATED = "install_secret_created"
    INSTALL_SECRET_PRESENT = "install_secret_present"
    INSTALL_SECRET_BYTES = "install_secret_bytes"
    STORE_IS_DPAPI = "store_is_dpapi"
    STORED_BLOB_IS_LARGER_THAN_SECRET = "stored_blob_is_larger_than_secret"
    # columns
    FIELDS_MAPPED = "fields_mapped"
    REQUIRED_UNMAPPED = "required_unmapped"
    QUESTIONS_OPEN = "questions_open"
    CHECKS_OK = "checks_ok"
    CHECKS_CHECK = "checks_check"
    CHECKS_PROBLEM = "checks_problem"
    DATE_QUESTIONS = "date_questions"
    DATE_BOTH_WAYS = "date_both_ways"
    SSN_SHAPED_IDS = "ssn_shaped_ids"
    PROCESS_BLOCKED = "process_blocked"
    # tidy
    STEPS_PROPOSED = "steps_proposed"
    STEPS_AMBER = "steps_amber"
    COLUMNS_ADDED = "columns_added"
    ROWS_FLAGGED = "rows_flagged"
    ZIP_FOUND = "zip_found"
    ZIP_KEPT = "zip_kept"
    ZIP_NOT_WORKED_OUT = "zip_not_worked_out"
    SOURCE_CELLS_CHANGED = "source_cells_changed"
    # standardize
    ROWS = "rows"
    COUNTED = "counted"
    NOT_COUNTED_YET = "not_counted_yet"
    SET_ASIDE = "set_aside"
    OUTSIDE_NYC = "outside_nyc"
    NO_FIXED_ADDRESS = "no_fixed_address"
    ADDRESS_PROBLEM = "address_problem"
    TO_PLACE = "to_place"
    VALUES_CHANGED = "values_changed"
    ENTERED_LOST = "entered_lost"
    REASON = "reason"


def emit(label, value, scope=None, out=None, field=None, reason=None):
    """Print `label [SCOPE] [FIELD] [REASON] value`. The value must be an int, the scope a source letter or a table like A.1,
    the field one of the built-in field names and the reason a registered reason ID. Fields and reasons are closed sets."""
    from wholecount.engine import reasons
    from wholecount.engine.schema import BUILTIN_KEYS

    if reason is not None and reason not in reasons.all_reasons():
        raise ValueError("reason must be a registered reason ID")

    if not isinstance(label, CountLabel):
        raise TypeError("label must be a CountLabel")
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("value must be an int")
    if scope is not None and not (isinstance(scope, str) and _SCOPE_RE.fullmatch(scope)):
        raise ValueError("scope must be a source letter")
    if field is not None and field not in BUILTIN_KEYS:
        raise ValueError("field must be a built-in field name")
    parts = [label.value] + ([scope] if scope else []) + ([field] if field else []) + ([reason] if reason else []) + [f"{value:,}"]
    print(" ".join(parts), file=out or sys.stdout)


def _event_name(violation):
    """The denied event's name, with any path argument dropped so no file name is printed."""
    if violation.startswith("import of "):
        return "import " + violation[len("import of "):]
    head = violation.split(" ", 1)[0]
    if head in ("open", "_winapi.CreateFile"):
        return head
    return violation


def emit_denied(violation, out=None):
    print("denied " + _event_name(violation), file=out or sys.stdout)


def _count_pins(path):
    from tools.offline_scan import lock_pins
    return len(lock_pins(path.read_text(encoding="utf-8"))) if path.exists() else 0


def _count_audit_ids():
    index = ROOT / "tests" / "audit" / "INDEX.md"
    if not index.exists():
        return 0
    return len(re.findall(r"^\| [ABC]-\d+ \|", index.read_text(encoding="utf-8"), re.M))


def cmd_check(args):
    sys.path.insert(0, str(ROOT))
    from tools.offline_rules import APPROVED_DISTS

    from wholecount import copy

    from wholecount.guard import OfflineViolation

    before = set(sys.modules)
    try:
        import wholecount.app_imports  # noqa: F401
    except OfflineViolation:
        pass  # Already in _violations. The counts still print, and the exit code says it failed.
    imported = len(set(sys.modules) - before)

    emit(CountLabel.PINS_RUNTIME, _count_pins(ROOT / "requirements.lock"))
    emit(CountLabel.PINS_DEV, _count_pins(ROOT / "requirements-dev.lock"))
    emit(CountLabel.APPROVED_DISTRIBUTIONS, len(APPROVED_DISTS))
    emit(CountLabel.CLAIMS_IN_REGISTRY, len(copy.claims()))
    emit(CountLabel.AUDIT_IDS_LISTED, _count_audit_ids())
    emit(CountLabel.MODULES_IMPORTED_UNDER_GUARD, imported)
    emit(CountLabel.GUARD_VIOLATIONS, len(_violations))
    if "--why" in args:
        for v in _violations:
            emit_denied(v)
    return 1 if _violations else 0


def cmd_read(args):
    """Counts per file, headed by its letter, then overall. Rows are keyed with a throwaway secret, so nothing is written."""
    import secrets

    from wholecount.engine.progress import NullSink
    from wholecount.engine.systems import LetterBook
    from wholecount.session.loader import load_files
    from wholecount.session.secret_store import InstallSecret

    paths = [pathlib.Path(a) for a in args]
    result = load_files(paths, NullSink(), InstallSecret(secrets.token_bytes(32)), LetterBook())
    for f in result.files:
        if f.status != "ok":
            continue
        a, L = f.accounting, f.letter
        tables = [t for t in result.tables if t.letter == L]
        rf = f.read_file
        for label, value in (
            (CountLabel.TABLES_FOUND, len(tables)),
            (CountLabel.TABLES_INCLUDED, sum(1 for t in tables if t.included)),
            (CountLabel.ROWS_INCLUDED, a.included),
            (CountLabel.ROWS_EXCLUDED, a.excluded),
            (CountLabel.ROWS_NON_TABLE, a.non_table),
            (CountLabel.ROWS_HEADER, a.header),
            (CountLabel.ROWS_ABOVE_HEADER, a.above_header),
            (CountLabel.ROWS_SHARED, a.shared_rows),
            (CountLabel.NON_EMPTY_ROWS, a.non_empty_rows),
            (CountLabel.BALANCED, int(a.balanced())),
            (CountLabel.CONTINUATION_BLOCKS, sum(1 for t in tables for b in t.blocks if b.continuation)),
            (CountLabel.SENSITIVE_COLUMNS_DROPPED, sum(len(t.sensitive_dropped) for t in tables)),
            (CountLabel.SENSITIVE_COLUMNS_BY_VALUES, sum(t.sensitive_by_values for t in tables)),
            (CountLabel.READ_AS_WINDOWS_TEXT, int(rf.encoding == "windows-1252")),
            (CountLabel.INVISIBLE_CHARACTERS_REMOVED, sum(rf.clean_counts.values())),
        ):
            emit(label, value, scope=L)
    counts = result.counts()
    emit(CountLabel.FILES_READ, counts["ok"])
    emit(CountLabel.FILES_UNREADABLE, counts["unreadable"])
    emit(CountLabel.FILES_DUPLICATE, counts["duplicate_file"])
    return 0


def cmd_secret(args):
    """The one dev command that writes a file: the install secret H9 allows. It never prints the secret."""
    from wholecount.session.secret_store import DpapiSecretStore, default_store, get_or_create_secret

    store = default_store()
    secret, created = get_or_create_secret(store)
    stored = store.path.stat().st_size if store.path.exists() else 0
    emit(CountLabel.INSTALL_SECRET_CREATED, int(created))
    emit(CountLabel.INSTALL_SECRET_PRESENT, 1)
    emit(CountLabel.INSTALL_SECRET_BYTES, len(secret._value))
    emit(CountLabel.STORE_IS_DPAPI, int(isinstance(store, DpapiSecretStore)))
    emit(CountLabel.STORED_BLOB_IS_LARGER_THAN_SECRET, int(stored > len(secret._value)))
    return 0


def cmd_columns(args):
    """Per included table (A.1, A.2 headed by letter and table number), the mapping's counts. No header or value is printed."""
    import secrets

    from wholecount.engine.dateorder import collect_evidence, decide
    from wholecount.engine.mapping import auto_map, check_mapping, process_blocks, profile_columns
    from wholecount.engine.progress import NullSink
    from wholecount.engine.schema import default_schema
    from wholecount.engine.systems import LetterBook
    from wholecount.session.loader import load_files
    from wholecount.session.secret_store import InstallSecret

    schema = default_schema()
    result = load_files([pathlib.Path(a) for a in args], NullSink(), InstallSecret(secrets.token_bytes(32)), LetterBook())
    numbers = {}
    for t in result.tables:
        numbers[t.letter] = numbers.get(t.letter, 0) + 1
        if not t.included:
            continue
        scope = f"{t.letter}.{numbers[t.letter]}"
        profiles = profile_columns(t)
        m = check_mapping(schema, auto_map(schema, profiles, t.key), profiles)
        blocks = process_blocks(schema, {t.key: m}, (), {t.key: profiles})
        statuses = [c.status for c in m.checks.values()]
        date_q = both = 0
        dob = m.column_for("Date_of_Birth")
        if dob is not None and not dob.derived:
            meta = {i: mm for (i, c), mm in t.meta.items() if c == dob.index}
            d = decide(collect_evidence([r[dob.index] for r in t.rows], meta))
            date_q = int(d.state in ("ask_no_evidence", "ask_both_ways"))
            both = int(d.state == "ask_both_ways")
        emit(CountLabel.FIELDS_MAPPED, len(m.assignments), scope=scope)
        for b in blocks:
            if b.kind == "missing_required":
                emit(CountLabel.REQUIRED_UNMAPPED, 1, scope=scope, field=b.field)
                if b.also:
                    emit(CountLabel.REQUIRED_UNMAPPED, 1, scope=scope, field=b.also)
        emit(CountLabel.QUESTIONS_OPEN, len(m.questions), scope=scope)
        emit(CountLabel.CHECKS_OK, statuses.count("ok"), scope=scope)
        emit(CountLabel.CHECKS_CHECK, statuses.count("check"), scope=scope)
        emit(CountLabel.CHECKS_PROBLEM, statuses.count("problem"), scope=scope)
        emit(CountLabel.DATE_QUESTIONS, date_q, scope=scope)
        emit(CountLabel.DATE_BOTH_WAYS, both, scope=scope)
        emit(CountLabel.SSN_SHAPED_IDS, sum(1 for b in blocks if b.kind == "ssn_shaped_id"), scope=scope)
        emit(CountLabel.PROCESS_BLOCKED, int(bool(blocks)), scope=scope)
    return 0


def cmd_tidy(args):
    """Per included table, the proposed tidy-up steps applied, in counts. No lookup is available, so a calculated ZIP finds none."""
    import secrets

    from wholecount.engine.mapping import auto_map, profile_columns
    from wholecount.engine.prepare.steps import apply_steps, propose_steps, source_cells_changed
    from wholecount.engine.progress import NullSink
    from wholecount.engine.schema import default_schema
    from wholecount.engine.systems import LetterBook
    from wholecount.session.loader import load_files
    from wholecount.session.secret_store import InstallSecret

    schema = default_schema()
    result = load_files([pathlib.Path(a) for a in args], NullSink(), InstallSecret(secrets.token_bytes(32)), LetterBook())
    numbers = {}
    for t in result.tables:
        numbers[t.letter] = numbers.get(t.letter, 0) + 1
        if not t.included:
            continue
        scope = f"{t.letter}.{numbers[t.letter]}"
        before = [list(r) for r in t.rows]
        steps = propose_steps(t, auto_map(schema, profile_columns(t), t.key))
        prepared = apply_steps(t, steps)
        zips = {}
        for r in prepared.results:
            for k, v in r.counts.items():
                zips[k] = zips.get(k, 0) + v
        emit(CountLabel.STEPS_PROPOSED, len(steps), scope=scope)
        emit(CountLabel.STEPS_AMBER, sum(1 for r in prepared.results if r.amber), scope=scope)
        emit(CountLabel.COLUMNS_ADDED, len(prepared.columns), scope=scope)
        for reason_id, n in sorted(prepared.reasons_by_id().items()):
            emit(CountLabel.ROWS_FLAGGED, n, scope=scope, reason=reason_id)
        emit(CountLabel.ZIP_FOUND, zips.get("found", 0), scope=scope)
        emit(CountLabel.ZIP_KEPT, zips.get("kept", 0), scope=scope)
        emit(CountLabel.ZIP_NOT_WORKED_OUT, zips.get("not_worked_out", 0), scope=scope)
        emit(CountLabel.SOURCE_CELLS_CHANGED, source_cells_changed(before, t), scope=scope)
    return 0


def _option(args, name):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else None
    return None


def cmd_standardize(args):
    """Per included table: load, map, proposed steps, standardize. Counts and reason IDs only.

    --today YYYY-MM-DD, --date-order month|day, --two-digit-pivot NN, and --choose-suggested-header, which applies a table's
    suggested header row the way an operator would on Show data."""
    import datetime as dt
    import secrets

    from wholecount.engine.dateorder import DateFieldSetting, DateOrder, TwoDigitRule, collect_evidence, decide
    from wholecount.engine.mapping import auto_map, profile_columns
    from wholecount.engine.prepare.steps import apply_steps, propose_steps
    from wholecount.engine.progress import NullSink
    from wholecount.engine.read.tables import rebuild_with_header
    from wholecount.engine.schema import default_schema
    from wholecount.engine.standardize.dates import date_context
    from wholecount.engine.standardize.inputs import build_inputs
    from wholecount.engine.standardize.rows import TableOptions, standardize_table
    from wholecount.engine.systems import LetterBook
    from wholecount.session.loader import key_tables, load_files
    from wholecount.session.secret_store import InstallSecret

    flags = {"--today", "--date-order", "--two-digit-pivot"}
    paths = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in flags)]
    today = dt.date.fromisoformat(_option(args, "--today")) if _option(args, "--today") else dt.date.today()
    order = {"month": DateOrder.MONTH_FIRST, "day": DateOrder.DAY_FIRST}.get(_option(args, "--date-order") or "")
    pivot = _option(args, "--two-digit-pivot")
    setting = DateFieldSetting(order, TwoDigitRule(int(pivot)) if pivot is not None else None)
    schema = default_schema()
    secret = InstallSecret(secrets.token_bytes(32))
    result = load_files([pathlib.Path(a) for a in paths], NullSink(), secret, LetterBook())
    numbers = {}
    for t in result.tables:
        numbers[t.letter] = numbers.get(t.letter, 0) + 1
        if not t.included and "--choose-suggested-header" in args and t.suggested_header_row and not t.header_is_virtual:
            fk = t.key.split(" :: ")[0]
            t = key_tables(secret, fk, [rebuild_with_header(t, t.suggested_header_row)])[0]
        if not t.included:
            continue
        scope = f"{t.letter}.{numbers[t.letter]}"
        mapping = auto_map(schema, profile_columns(t), t.key)
        prepared = apply_steps(t, propose_steps(t, mapping))
        mapping = auto_map(schema, profile_columns(t, prepared.column_refs()), t.key)
        contexts = {}
        dob = mapping.column_for("Date_of_Birth")
        if dob is not None:
            meta = {} if dob.derived else {i: m for (i, c), m in t.meta.items() if c == dob.index}
            contexts["Date_of_Birth"] = date_context(decide(collect_evidence(prepared.values(dob.name), meta)), setting)
        inputs = build_inputs(prepared, mapping, (), schema)
        rows = standardize_table(inputs, schema, TableOptions(contexts), today)
        counted = [r for r in rows if r.count_status.counted]
        loc = [r.location for r in counted]
        changed = sum(1 for r in rows for v in r.values.values() if v.value != v.entered)
        lost = sum(1 for r, i in zip(rows, inputs) for k, v in r.values.items() if v.entered != i.values.get(k, ""))
        emit(CountLabel.ROWS, len(rows), scope=scope)
        emit(CountLabel.COUNTED, len(counted), scope=scope)
        emit(CountLabel.NOT_COUNTED_YET, sum(1 for r in rows if r.count_status.value == "not_counted_yet"), scope=scope)
        emit(CountLabel.SET_ASIDE, sum(1 for r in rows if r.count_status.value == "set_aside"), scope=scope)
        for label, reason in ((CountLabel.OUTSIDE_NYC, "outside_nyc"), (CountLabel.NO_FIXED_ADDRESS, "no_fixed_address"),
                              (CountLabel.ADDRESS_PROBLEM, "address_problem")):
            emit(label, sum(1 for x in loc if x.reason == reason), scope=scope)
        emit(CountLabel.TO_PLACE, sum(1 for x in loc if x.kind == "to_place"), scope=scope)
        emit(CountLabel.VALUES_CHANGED, changed, scope=scope)
        emit(CountLabel.ENTERED_LOST, lost, scope=scope)
        tally = {}
        for r in rows:
            for ref in r.reasons:
                tally[ref.reason_id] = tally.get(ref.reason_id, 0) + 1
        for rid, n in sorted(tally.items()):
            emit(CountLabel.REASON, n, scope=scope, reason=rid)
    return 0


COMMANDS = {"check": cmd_check, "read": cmd_read, "secret": cmd_secret, "columns": cmd_columns, "tidy": cmd_tidy,
            "standardize": cmd_standardize}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print("usage: python -m wholecount.dev {" + ",".join(sorted(COMMANDS)) + "}", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
