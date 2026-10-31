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
    # geo-status
    BACKEND_GEOSUPPORT = "backend_geosupport"
    BACKEND_REFERENCE = "backend_reference"
    BACKEND_NONE = "backend_none"
    RELEASE_KNOWN = "release_known"
    RELEASE_YEAR = "release_year"
    RELEASE_QUARTER = "release_quarter"
    RELEASE_STALE = "release_stale"
    REFERENCE_REAL = "reference_real"
    REFERENCE_SAMPLE = "reference_sample"
    REFERENCE_ROWS = "reference_rows"
    REFERENCE_FILES_SEVERAL = "reference_files_several"
    DISTRICT_FILES = "district_files"
    CAN_PLACE = "can_place"
    # geo-check
    LOOKED_UP = "looked_up"
    PLACED_HIGH = "placed_high"
    PLACED_LOW = "placed_low"
    NOT_PLACED = "not_placed"
    DISTRICTS_FILLED = "districts_filled"
    # offset-demo
    SAME_OFFSET_SECOND_RUN = "same_offset_second_run"
    DISTANCE_IN_RANGE = "distance_in_range"
    DISTANCE_FEET = "distance_feet"
    ONE_BUILDING_ONE_POINT = "one_building_one_point"
    OTHER_SECRET_DIFFERS = "other_secret_differs"
    # map-demo
    CELLS_TOTAL = "cells_total"
    CELLS_BLANKED = "cells_blanked"
    ROWS_WITH_A_NAME = "rows_with_a_name"
    # people-demo and people-check
    ROWS_READ = "rows_read"
    COPY_GROUPS = "copy_groups"
    COPY_GROUPS_IDENTICAL = "copy_groups_identical"
    COPY_GROUPS_POSSIBLE = "copy_groups_possible"
    COPY_GROUPS_SAME_ID_DIFFERENT = "copy_groups_same_id_different"
    AUTOMATIC_JOINS = "automatic_joins"
    JOINS_FOUR_EXACT_FACTS = "joins_four_exact_facts"
    JOINS_SAME_SYSTEM_ID = "joins_same_system_id"
    PROPOSALS = "proposals"
    PROPOSALS_LIKELY = "proposals_likely"
    PROPOSALS_POSSIBLE = "proposals_possible"
    NAME_ONLY_PROPOSALS = "name_only_proposals"
    PEOPLE_LOW = "people_low"
    PEOPLE_HIGH = "people_high"
    MASTER_IDS_UNIQUE = "master_ids_unique"
    SKIPPED_BUCKETS = "skipped_buckets"
    # programs-demo and programs-check
    PAIRS_THAT_SHOULD_MATCH = "pairs_that_should_match"
    PAIRS_MATCHED = "pairs_matched"
    PAIRS_THAT_SHOULD_NOT_MATCH = "pairs_that_should_not_match"
    PAIRS_LEFT_ALONE = "pairs_left_alone"
    CHAINS_GROUPED = "chains_grouped"
    DISTINCT_NAMES = "distinct_names"
    PROPOSALS_SAME_NAME = "proposals_same_name"
    PROPOSALS_INITIALS = "proposals_initials"
    PROPOSALS_NEARLY_SAME = "proposals_nearly_same"
    PROPOSALS_MORE_WORDS = "proposals_more_words"
    NAMES_LEFT_ALONE = "names_left_alone"
    ROWS_WITHOUT_PROGRAM = "rows_without_program"
    # session-demo and session-check
    STAGE = "stage"
    RECEIVED = "received"
    GOAL1_LOW = "goal1_low"
    GOAL1_HIGH = "goal1_high"
    GOAL2_LOW = "goal2_low"
    GOAL2_HIGH = "goal2_high"
    OPEN_PAIRS = "open_pairs"
    OPEN_COPY_GROUPS = "open_copy_groups"
    CONFIDENCE_LEVEL = "confidence_level"
    BALANCE_OK = "balance_ok"
    FINAL = "final"
    MAPPED = "mapped"
    COUNTED_NOT_MAPPED = "counted_not_mapped"
    NOT_FOUND = "not_found"
    NO_GEOCODER = "no_geocoder"
    DOB_COVERAGE_PCT = "dob_coverage_pct"
    STEP_1_TENTHS = "step_1_tenths"
    STEP_2_TENTHS = "step_2_tenths"
    STEP_3_TENTHS = "step_3_tenths"
    STEP_4_TENTHS = "step_4_tenths"
    DECISIONS_MADE = "decisions_made"
    DECISIONS_KEPT = "decisions_kept"
    NO_LONGER_APPLY = "no_longer_apply"
    # M09 outputs and saved progress
    DPAPI_ROUND_TRIP = "dpapi_round_trip"
    CHANGED_BYTE_DETECTED = "changed_byte_detected"
    FILES_WRITTEN = "files_written"
    CLEAN_ROWS = "clean_rows"
    REVIEW_ROWS = "review_rows"
    SET_ASIDE_ROWS = "set_aside_rows"
    UNIQUE_CLIENTS_ROWS = "unique_clients_rows"
    BY_PROGRAM_ROWS = "by_program_rows"
    FOLDER_WARNING = "folder_warning"
    CORRECTIONS_ACCEPTED = "corrections_accepted"
    CORRECTIONS_REFUSED = "corrections_refused"
    REFUSED_OTHER_COLUMN = "refused_other_column"
    FILE_BYTES = "file_bytes"
    DECRYPTS_FOR_THIS_USER = "decrypts_for_this_user"
    CELL_VALUES_FOUND = "cell_values_found"
    DECISIONS_RESTORED = "decisions_restored"
    DELETED = "deleted"
    # M13 backup, crosswalk and calibration
    BACKUP_BYTES = "backup_bytes"
    KNOWN_ANSWER_MATCHES = "known_answer_matches"
    RESTORE_OK = "restore_ok"
    WRONG_PASSPHRASE_REFUSED = "wrong_passphrase_refused"
    ONE_CHANGED_BYTE_REFUSED = "one_changed_byte_refused"
    PEOPLE = "people"
    PERSON_KEYS = "person_keys"
    PAIR_VERDICTS = "pair_verdicts"
    PROGRAM_GROUPS = "program_groups"
    MERGED = "merged"
    WAL_FILES = "wal_files"
    LABELED_PAIRS = "labeled_pairs"
    REGRESSION_DROPPED = "regression_dropped"
    # perf (M15): times in milliseconds, memory in MB
    ADD_FILES_MS = "add_files_ms"
    PROCESS_MS = "process_ms"
    PREVIEW_MS = "preview_ms"
    DOWNLOAD_MS = "download_ms"
    REDRAW_MAX_MS = "redraw_max_ms"
    DECISION_MS = "decision_ms"
    PEAK_MEMORY_MB = "peak_memory_mb"
    FILES = "files"


def emit(label, value, scope=None, out=None, field=None, reason=None, grouped=True):
    """Print `label [SCOPE] [FIELD] [REASON] value`. The value must be an int, the scope a source letter or a table like A.1,
    the field one of the built-in field names and the reason a registered reason ID. Fields and reasons are closed sets. A year is
    printed with grouped=False, so 2025 doesn't read as 2,025."""
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
    shown = f"{value:,}" if grouped else str(value)
    parts = [label.value] + ([scope] if scope else []) + ([field] if field else []) + ([reason] if reason else []) + [shown]
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


def _geo_preflight(today):
    import os

    from wholecount.engine.geo.backend import preflight
    from wholecount.paths import data_dir

    return preflight(os.environ, data_dir(), today)


def cmd_geo_status(args):
    """Which backend a batch of the operator's own files would use, its release, the reference and district files. Counts only."""
    import datetime as dt

    from wholecount.engine.geo.geosupport import release_quarter

    today = dt.date.fromisoformat(_option(args, "--today")) if _option(args, "--today") else dt.date.today()
    pf = _geo_preflight(today)
    name = pf.backend_name
    rq = release_quarter(pf.release)
    emit(CountLabel.BACKEND_GEOSUPPORT, int(name == "geosupport"))
    emit(CountLabel.BACKEND_REFERENCE, int(name == "reference"))
    emit(CountLabel.BACKEND_NONE, int(name == "none"))
    emit(CountLabel.RELEASE_KNOWN, int(rq is not None))
    emit(CountLabel.RELEASE_YEAR, rq[0] if rq else 0, grouped=False)
    emit(CountLabel.RELEASE_QUARTER, rq[1] if rq else 0)
    emit(CountLabel.RELEASE_STALE, int(pf.release_stale))
    emit(CountLabel.REFERENCE_REAL, int(pf.reference_kind == "real"))
    emit(CountLabel.REFERENCE_SAMPLE, int(pf.reference_kind == "sample"))
    emit(CountLabel.REFERENCE_ROWS, pf.reference_rows)
    emit(CountLabel.REFERENCE_FILES_SEVERAL, int(pf.reference_kind == "several_reference_files"))
    emit(CountLabel.DISTRICT_FILES, pf.district_files)
    emit(CountLabel.CAN_PLACE, int(pf.can_place))
    return 0


def cmd_geo_check(args):
    """Look up the 12 landmarks in tests_windows/landmarks.csv, or a CSV's rows with --csv PATH --house COL --street COL
    --zip COL, through the backend preflight picks. Counts only, never an address."""
    import csv
    import datetime as dt

    from wholecount.engine.geo.backend import district_paths
    from wholecount.engine.geo.districts import DistrictIndex

    pf = _geo_preflight(dt.date.today())
    backend = pf.backend
    districts = DistrictIndex.from_files(district_paths())
    path = _option(args, "--csv")
    cols = (_option(args, "--house") or "house", _option(args, "--street") or "street", _option(args, "--zip") or "zip")
    path = pathlib.Path(path) if path else ROOT / "tests_windows" / "landmarks.csv"
    tally = {"looked_up": 0, "high": 0, "low": 0, "not_placed": 0, "districts": 0}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            house, street, z = (row.get(c, "") or "" for c in cols)
            tally["looked_up"] += 1
            try:
                res = backend.lookup(house.strip(), street.strip(), z.strip()[:5])
            except Exception:
                tally["not_placed"] += 1
                continue
            if not res.placed:
                tally["not_placed"] += 1
                continue
            tally[res.confidence] += 1
            d = res.districts
            if d is None and res.source != "geosupport" and not districts.empty:
                d = districts.assign(res.latitude, res.longitude)
            tally["districts"] += int(d is not None and d.any())
    emit(CountLabel.LOOKED_UP, tally["looked_up"])
    emit(CountLabel.PLACED_HIGH, tally["high"])
    emit(CountLabel.PLACED_LOW, tally["low"])
    emit(CountLabel.NOT_PLACED, tally["not_placed"])
    emit(CountLabel.DISTRICTS_FILLED, tally["districts"])
    return 0


def cmd_offset_demo(args):
    """The privacy offset on a made-up building with two throwaway secrets. It never reads or writes the install secret."""
    import secrets

    from wholecount.engine.geo.mapdata import MapPointEntry, build_map_points
    from wholecount.engine.geo.offset import PrivacyOffset, haversine_ft
    from wholecount.session.secret_store import InstallSecret

    key, lat, lon = "125|worth street|10013", 40.7160, -74.0040
    one, two = InstallSecret(secrets.token_bytes(32)), InstallSecret(secrets.token_bytes(32))
    first = PrivacyOffset.from_settings(one.mac).apply(key, lat, lon)
    second = PrivacyOffset.from_settings(one.mac).apply(key, lat, lon)
    other = PrivacyOffset.from_settings(two.mac).apply(key, lat, lon)
    feet = haversine_ft(lat, lon, *first)
    points = build_map_points([MapPointEntry("Program", key, lat, lon) for _ in range(25)], one.mac)
    emit(CountLabel.SAME_OFFSET_SECOND_RUN, int(first == second))
    emit(CountLabel.DISTANCE_IN_RANGE, int(150 - 0.5 <= feet <= 250 + 0.5))
    emit(CountLabel.DISTANCE_FEET, round(feet))
    emit(CountLabel.ONE_BUILDING_ONE_POINT, int(len({(p.latitude, p.longitude) for p in points}) == 1))
    emit(CountLabel.OTHER_SECRET_DIFFERS, int(other != first))
    return 0


def cmd_map_demo(args):
    """Map_Counts rows for made-up entries: some cells are small and blanked. No row carries a name, ID or point."""
    import dataclasses

    from wholecount.engine.geo.mapdata import MapEntry, build_map_counts, small_cell_max
    from wholecount.engine.geo.types import Districts

    entries = []
    for i in range(60):
        entries.append(MapEntry(f"u{i}", "Program A" if i % 3 else "Program B",
                                Districts(str(10 + i % 2), str(60 + i % 4), str(1 + i % 7))))
    rows = build_map_counts(entries, small_cell_max())
    named = {"unit", "name", "given", "surname", "client_id", "master_id", "address", "latitude", "longitude"}
    emit(CountLabel.CELLS_TOTAL, len(rows))
    emit(CountLabel.CELLS_BLANKED, sum(1 for r in rows if r.count is None))
    emit(CountLabel.ROWS_WITH_A_NAME, sum(1 for r in rows if named & {f.name for f in dataclasses.fields(r)}))
    return 0


# The 12 records of the C-01 audit fixture: two systems, made-up people. people-demo builds them in memory only.
_C01 = (("A", "A1", "Maria", "Rodriguez", "1985-03-14", "100", "Grand Concourse", "10451"),
        ("A", "A2", "Jordan", "Smith", "2015-06-01", "10", "Oak St", "11201"),
        ("A", "A3", "Robert", "Smith", "1962-03-14", "20", "Elm St", "11201"),
        ("A", "A4", "Ana", "Perez", "1990-05-06", "7", "Elm St", "10013"),
        ("A", "A5", "Luis", "Diaz", "1980-02-02", "123", "45th St", "11377"),
        ("A", "A6", "Carlos", "Vega", "1975-01-01", "5", "A St", "10001"),
        ("B", "B1", "Maria", "Rodriguez", "1985-03-14", "100", "Grand Concourse", "10451"),
        ("B", "B2", "Jaden", "Smith", "2015-06-01", "10", "Oak St", "11201"),
        ("B", "B3", "Robert", "Smith Jr", "1992-03-14", "20", "Elm St", "11201"),
        ("B", "B4", "Ana", "Perez", "1990-06-05", "7", "Elm St", "10013"),
        ("B", "B5", "Luis", "Diaz", "1980-02-02", "123", "45th Ave", "11377"),
        ("B", "B6", "Elena", "Vega", "1999-09-09", "6", "B St", "10001"))


def _emit_identity(result):
    joins = result.auto_joins
    emit(CountLabel.AUTOMATIC_JOINS, len(joins))
    emit(CountLabel.JOINS_FOUR_EXACT_FACTS, sum(1 for j in joins if j.reason == "four_exact_facts"))
    emit(CountLabel.JOINS_SAME_SYSTEM_ID, sum(1 for j in joins if j.reason == "same_system_id"))
    emit(CountLabel.PROPOSALS_LIKELY, sum(1 for p in result.proposals if p.band == "likely"))
    emit(CountLabel.PROPOSALS_POSSIBLE, sum(1 for p in result.proposals if p.band == "possible"))
    emit(CountLabel.NAME_ONLY_PROPOSALS, sum(1 for p in result.proposals if p.found_via == ("K4",)))
    emit(CountLabel.PEOPLE_LOW, result.low)
    emit(CountLabel.PEOPLE_HIGH, result.settled)
    emit(CountLabel.MASTER_IDS_UNIQUE, int(len(set(result.groups)) == result.settled))
    emit(CountLabel.SKIPPED_BUCKETS, result.skipped_buckets)


def cmd_people_demo(args):
    """The C-01 fixture through identity, keyed with a throwaway secret. Counts only."""
    import secrets

    from wholecount.engine.addresskey import address_key
    from wholecount.engine.identity import PersonRow, resolve
    from wholecount.session.keys import person_key
    from wholecount.session.secret_store import InstallSecret

    secret = InstallSecret(secrets.token_bytes(32))
    rows = [PersonRow(cid, person_key(secret, system, client_id=cid), system, cid, first, last, dob,
                      address_key(house, street, zip5), "", zip5, "Housing")
            for system, cid, first, last, dob, house, street, zip5 in _C01]
    _emit_identity(resolve(rows))
    return 0


def _iso_dob(text):
    import re

    t = text.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        return t
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def cmd_people_check(args):
    """Copies and identity over one or more CSV files: --csv PATH --system NAME (repeat both), with --first --last --dob
    --client-id --address --zip --program naming the columns. It writes nothing and prints counts only."""
    import csv
    import secrets

    from wholecount.engine.addresskey import address_key, split_house_street
    from wholecount.engine.copies import CopyRow, TableInfo, find_copies, key_modes
    from wholecount.engine.fold import fold
    from wholecount.engine.identity import PersonRow, resolve
    from wholecount.session.keys import person_key
    from wholecount.session.secret_store import InstallSecret

    paths = [args[i + 1] for i, a in enumerate(args) if a == "--csv" and i + 1 < len(args)]
    systems = [args[i + 1] for i, a in enumerate(args) if a == "--system" and i + 1 < len(args)]
    systems += [chr(65 + i) for i in range(len(systems), len(paths))]
    col = {name: _option(args, f"--{name}") or default for name, default in (
        ("first", "First_Name"), ("last", "Last_Name"), ("dob", "Date_of_Birth"), ("client-id", "Client_ID"),
        ("address", "Address_1"), ("zip", "Zip"), ("program", "Program"))}
    secret = InstallSecret(secrets.token_bytes(32))
    copy_rows, tables = [], {}
    for n, (path, system) in enumerate(zip(paths, systems)):
        table = f"t{n}"
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            tables[table] = TableInfo(col["dob"] in (reader.fieldnames or ()), system)
            for i, row in enumerate(reader):
                get = lambda c: (row.get(col[c]) or "").strip()  # noqa: E731
                house, street = split_house_street(get("address"))
                z = get("zip")[:5]
                akey = address_key(house, street, z) if house else ""
                copy_rows.append(CopyRow(f"{table}:{i:07d}", table, system, get("client-id"), get("first"), "", get("last"),
                                         _iso_dob(get("dob")), akey, get("program"), tuple(sorted(row.items()))))
    groups = find_copies(copy_rows, tables)
    emit(CountLabel.ROWS_READ, len(copy_rows))
    emit(CountLabel.COPY_GROUPS, len(groups))
    for label, kind in ((CountLabel.COPY_GROUPS_IDENTICAL, "identical"), (CountLabel.COPY_GROUPS_POSSIBLE, "possible"),
                        (CountLabel.COPY_GROUPS_SAME_ID_DIFFERENT, "same_id_different")):
        emit(label, sum(1 for g in groups if g.kind == kind))
    held = {m for g in groups if g.kind == "same_id_different" for m in g.members}
    modes = key_modes(groups, {}, rows=copy_rows)
    people = []
    for c in copy_rows:
        if c.record_key in held:
            continue
        if modes.get(c.record_key) == "row":
            k = person_key(secret, "row", client_id=c.record_key)
        elif c.client_id:
            k = person_key(secret, c.system, client_id=c.client_id)
        else:
            k = person_key(secret, c.system, given=fold(c.first), surname=fold(c.last), dob=c.dob or None, address_key=c.address_key)
        zip5 = (dict(c.values).get(col["zip"]) or "").strip()[:5]
        people.append(PersonRow(c.record_key, k, c.system, c.client_id, c.first, c.last, c.dob, c.address_key, "", zip5,
                                c.program))
    open_groups = [g.members for g in groups if g.kind != "same_id_different"]
    result = resolve(people, open_copy_groups=open_groups)
    emit(CountLabel.PROPOSALS, len(result.proposals))
    _emit_identity(result)
    return 0


# The B-40 program names: made-up names the audit used. programs-demo runs them in memory.
_B40_MATCH = (("Workforce Dev.", "Workforce Development"), ("WFD", "Workforce Development"), ("WFD", "Workforce Dev."),
              ("SYEP", "Summer Youth Employment Program"), ("Summer Youth Employment", "Summer Youth Employment Program"),
              ("Workforce", "Workforce Development"), ("youth", "Youth"))
_B40_APART = (("Youth Services", "Youth Employment"), ("Youth Services", "Youth Housing"), ("Youth Employment", "Youth Housing"),
              ("Senior Services", "Senior Housing"), ("Senior Services", "Senior Employment"), ("Senior Housing", "Senior Employment"),
              ("Level 1", "Level 2"), ("Cohort 2023", "Cohort 2024"), ("Section B", "Section C"), ("ESL Level 1", "ESL Level 2"),
              ("ESL 1", "ESL 2"), ("Tier 1", "Tier 2"), ("3K", "4K"), ("Group A", "Group B"), ("Class A", "Class B"),
              ("Adult", "Adult Day Care"), ("Adult Education", "Adult"), ("Adult", "Adult Literacy"),
              ("Adult Education", "Adult Literacy"), ("GED", "GED Prep"),
              ("Health", "Hospital Employment Assistance Linkage Training Hub"), ("Pre-K", "Pre-K Extended Day"),
              ("Tenant Services", "Tenant Organizing"), ("Food Pantry", "Food Stamps"), ("Youth Employment", "Youth Empowerment"),
              ("Mental Health", "Mental Hygiene"), ("Housing Counseling", "Housing Court"))
_B40_CHAINS = (("Youth Services", "Youth Employment", "Youth Housing"), ("Senior Services", "Senior Housing", "Senior Employment"),
               ("Adult Education", "Adult", "Adult Literacy"))


def cmd_programs_demo(args):
    """The B-40 pairs and chains through propose_groups. Counts only."""
    from wholecount.engine.programs import ProgramName, propose_groups

    def proposed(names):
        return propose_groups([ProgramName(n, 1) for n in names])

    emit(CountLabel.PAIRS_THAT_SHOULD_MATCH, len(_B40_MATCH))
    emit(CountLabel.PAIRS_MATCHED, sum(1 for p in _B40_MATCH if proposed(p)))
    emit(CountLabel.PAIRS_THAT_SHOULD_NOT_MATCH, len(_B40_APART))
    emit(CountLabel.PAIRS_LEFT_ALONE, sum(1 for p in _B40_APART if not proposed(p)))
    emit(CountLabel.CHAINS_GROUPED, sum(1 for c in _B40_CHAINS for g in proposed(c) if len(g.members) == 3))
    return 0


def cmd_programs_check(args):
    """Program names in one or more CSV files: --csv PATH (repeat) --column NAME. Counts only, never a program name."""
    import csv

    from wholecount.engine.programs import TableProgram, program_sources, propose_groups

    paths = [args[i + 1] for i, a in enumerate(args) if a == "--csv" and i + 1 < len(args)]
    column = _option(args, "--column") or "Program"
    tables, blank = [], 0
    for n, path in enumerate(paths):
        counts, rows, has = {}, 0, False
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            has = column in (reader.fieldnames or ())
            for row in reader:
                rows += 1
                v = (row.get(column) or "").strip()
                counts[v] = counts.get(v, 0) + 1
        blank += counts.get("", 0) if has else rows
        tables.append(TableProgram(f"t{n}", "column" if has else "none", column if has else None, None, rows,
                                   tuple(sorted(counts.items()))))
    names, _ = program_sources(tables)
    proposals = propose_groups(names)
    reasons = [r for p in proposals for r in {x[2] for x in p.reasons}]
    emit(CountLabel.DISTINCT_NAMES, len(names))
    emit(CountLabel.PROPOSALS, len(proposals))
    for label, code in ((CountLabel.PROPOSALS_SAME_NAME, "same_name"), (CountLabel.PROPOSALS_INITIALS, "initials"),
                        (CountLabel.PROPOSALS_NEARLY_SAME, "nearly_same"), (CountLabel.PROPOSALS_MORE_WORDS, "more_words")):
        emit(label, reasons.count(code))
    emit(CountLabel.NAMES_LEFT_ALONE, len(names) - sum(len(p.members) for p in proposals))
    emit(CountLabel.ROWS_WITHOUT_PROGRAM, blank)
    return 0


# The R and S fixture of M08: made-up people. session-demo writes them to a temporary folder that's removed afterward.
_R_ROWS = [["R01", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R02", "Ben", "Cruz", "1981-02-02", "12 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R03", "Cara", "Diaz", "1982-03-03", "14 Oak St", "Brooklyn", "NY", "11201", "Youth"],
           ["R04", "Dev", "Rao", "1983-04-04", "16 Oak St", "Brooklyn", "NY", "11201", "Youth"],
           ["R05", "Eli", "Fox", "1984-05-05", "18 Oak St", "Brooklyn", "NY", "11201", "Workforce"],
           ["R06", "Fay", "Gil", "1985-06-06", "20 Oak St", "Brooklyn", "NY", "11201", "Workforce"],
           ["R07", "Gus", "Hall", "1986-07-07", "22 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R07", "Gus", "Hall", "1986-07-07", "22 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R09", "Hana", "Ito", "1987-08-08", "24 Oak St", "Brooklyn", "NY", "11201", "Youth"],
           ["R10", "HANA", "ITO", "1987-08-08", "24 Oak St", "Brooklyn", "NY", "11201", "Youth"],
           ["R11", "Ivy", "Jones", "1988-09-09", "26 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R11", "Jon", "Kane", "1975-10-10", "28 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["R13", "Kim", "Lu", "1989-11-11", "85 Montague St", "Brooklyn", "NY", "", "Workforce"],
           ["R14", "", "Moss", "1990-12-12", "30 Oak St", "Brooklyn", "NY", "11201", "Youth"],
           ["", "Total", "", "", "", "", "", "", ""]]
_S_ROWS = [["S1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
           ["S2", "Ben", "Cruz", "1981-02-02", "99 Elm St", "Brooklyn", "NY", "11201", "Housing"]]
_R_HEADER = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
_R_POINTS = [(str(n), "Oak St", "11201", "Brooklyn", 40.690 + n / 10000, -73.990) for n in (10, 12, 14, 16, 22, 24, 26, 28, 30)] + [
    ("85", "Montague St", "11201", "Brooklyn", 40.6940, -73.9930), ("99", "Elm St", "11201", "Brooklyn", 40.6950, -73.9800)]
_LEVEL = {None: 0, "low": 1, "medium": 2, "high": 3}


def _emit_session(s, stage):
    from wholecount.engine.counts import BalanceError, assert_balance

    r = s.results
    c = r.counts
    try:
        assert_balance(r.balance, r.outcomes.values())
        ok = 1
    except BalanceError:
        ok = 0
    emit(CountLabel.STAGE, stage)
    for label, value in ((CountLabel.RECEIVED, c.received), (CountLabel.COUNTED, c.counted),
                         (CountLabel.NOT_COUNTED_YET, c.not_counted_yet), (CountLabel.SET_ASIDE, c.set_aside),
                         (CountLabel.GOAL1_LOW, c.goal1.low), (CountLabel.GOAL1_HIGH, c.goal1.high),
                         (CountLabel.GOAL2_LOW, c.goal2.low), (CountLabel.GOAL2_HIGH, c.goal2.high),
                         (CountLabel.OPEN_PAIRS, c.open_pairs), (CountLabel.OPEN_COPY_GROUPS, c.open_copy_groups),
                         (CountLabel.CONFIDENCE_LEVEL, _LEVEL[r.confidence.level]), (CountLabel.BALANCE_OK, ok),
                         (CountLabel.FINAL, int(c.final))):
        emit(label, value)


def cmd_session_demo(args):
    """The R and S fixture through the session: the base state, five decisions, two pair verdicts, then every undo."""
    import csv
    import datetime as dt
    import secrets
    import tempfile

    from wholecount.engine.geo.reference import ReferenceBackend
    from wholecount.session import commands as C
    from wholecount.session.runner import process
    from wholecount.session.secret_store import InstallSecret
    from wholecount.session.state import Session

    ref = ReferenceBackend.from_text("house_number,street,zip,borough,latitude,longitude\n"
                                     + "".join(",".join(map(str, p)) + "\n" for p in _R_POINTS))
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, rows in (("R.csv", _R_ROWS), ("S.csv", _S_ROWS)):
            path = pathlib.Path(tmp) / name
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(_R_HEADER)
                w.writerows(rows)
            paths.append(path)
        s = Session(InstallSecret(secrets.token_bytes(32)), paths, backend=ref, today=lambda: dt.date(2026, 10, 30),
                    getuser=lambda: "demo")
        process(s)
        _emit_session(s, 0)

        def rk(cid):
            return min(k for k, r in s.results.rows.items() if r.value("Client_ID") == cid)

        def grp(kind):
            return next(g for g in s.results.groups if g.kind == kind)

        steps = [lambda: C.KeepOneInCopyGroup(grp("identical").group_id, grp("identical").members[0]),
                 lambda: C.MarkNotCopies(grp("possible").group_id),
                 lambda: C.DecideSameIdConflict(grp("same_id_different").group_id, "approved_as_entered"),
                 lambda: C.AcceptFills([rk("R13")]), lambda: C.SetAsideRows([rk("R14")], "out_of_scope")]
        for make in steps:
            s.history.execute(make())
        _emit_session(s, 1)
        for p in list(s.results.identity.proposals):
            s.history.execute(C.DecidePair(*p.pair, "different"))
        _emit_session(s, 2)
        stage = 3
        while s.history.undo() is not None:
            _emit_session(s, stage)
            stage += 1
    return 0


class _TimingSink:
    """Times each step the runner reports, in tenths of a second. dev.py is not engine or session code, so it may read time."""

    def __init__(self):
        import time

        self._now = time.monotonic
        self.started, self.tenths, self.order = {}, {}, []

    def begin(self, step_id, total, unit):
        self.started[step_id] = self._now()
        if step_id not in self.order:
            self.order.append(step_id)

    def advance(self, n, message):
        pass

    def end(self, found):
        step = self.order[-1]
        self.tenths[step] = self.tenths.get(step, 0) + round((self._now() - self.started[step]) * 10)

    def cancelled(self):
        return False


def cmd_session_check(args):
    """Process one or more CSV files through the session: --csv PATH (repeat), with --shuffle-rows, --exclude-last,
    --decide-approve-all and --process-twice. Counts only. It writes nothing: rows are shuffled in memory."""
    import datetime as dt
    import os
    import secrets

    from wholecount.engine.counts import BalanceError, assert_balance
    from wholecount.paths import data_dir
    from wholecount.engine.geo.backend import preflight
    from wholecount.session import commands as C
    from wholecount.session.runner import _load, process
    from wholecount.session.secret_store import InstallSecret
    from wholecount.session.state import Session

    paths = [pathlib.Path(args[i + 1]) for i, a in enumerate(args) if a == "--csv" and i + 1 < len(args)]
    if "--exclude-last" in args and len(paths) > 1:
        paths = paths[:-1]
    backend = preflight(os.environ, data_dir(), dt.date.today()).backend
    s = Session(InstallSecret(secrets.token_bytes(32)), paths, backend=backend)
    sink = _TimingSink()
    if "--shuffle-rows" in args:
        load = _load(s, sink)
        for t in load.tables:
            order = sorted(range(len(t.rows)), key=lambda i: t.record_keys[i] if t.record_keys else i)
            t.rows = [t.rows[i] for i in order]
            t.row_numbers = [t.row_numbers[i] for i in order]
            t.row_block = [t.row_block[i] for i in order]
            t.record_keys = [t.record_keys[i] for i in order]
            new_index = {old: new for new, old in enumerate(order)}
            t.meta = {(new_index[r], c): m for (r, c), m in t.meta.items()}
    process(s, sink)
    made = 0
    if "--decide-approve-all" in args:
        keys = [k for k, o in s.results.outcomes.items()
                if set(o.reasons) - {"same_id_conflict"} and o.set_aside_reason is None]
        if keys:
            s.history.execute(C.ApproveRows(keys, "*", second="dev check" if len(keys) > 200 else None))
            made = len(s.decisions)
    if "--process-twice" in args:
        process(s, sink)
    r = s.results
    c = r.counts
    try:
        assert_balance(r.balance, r.outcomes.values())
        ok = 1
    except BalanceError:
        ok = 0
    locs = c.locations
    emit(CountLabel.BALANCE_OK, ok)
    for label, value in ((CountLabel.RECEIVED, c.received), (CountLabel.COUNTED, c.counted),
                         (CountLabel.NOT_COUNTED_YET, c.not_counted_yet), (CountLabel.SET_ASIDE, c.set_aside),
                         (CountLabel.MAPPED, locs.mapped), (CountLabel.COUNTED_NOT_MAPPED, locs.not_mapped),
                         (CountLabel.NO_FIXED_ADDRESS, locs.no_fixed_address), (CountLabel.OUTSIDE_NYC, locs.outside_nyc),
                         (CountLabel.ADDRESS_PROBLEM, locs.address_problem), (CountLabel.NOT_FOUND, locs.not_found),
                         (CountLabel.NO_GEOCODER, locs.no_geocoder), (CountLabel.GOAL1_LOW, c.goal1.low),
                         (CountLabel.GOAL1_HIGH, c.goal1.high), (CountLabel.GOAL2_LOW, c.goal2.low),
                         (CountLabel.GOAL2_HIGH, c.goal2.high), (CountLabel.OPEN_PAIRS, c.open_pairs),
                         (CountLabel.CONFIDENCE_LEVEL, _LEVEL[r.confidence.level]),
                         (CountLabel.DOB_COVERAGE_PCT, c.dob_coverage[0] * 100 // c.dob_coverage[1] if c.dob_coverage[1] else 0)):
        emit(label, value)
    if "--decide-approve-all" in args:
        emit(CountLabel.DECISIONS_MADE, made)
        emit(CountLabel.DECISIONS_KEPT, r.kept)
        emit(CountLabel.NO_LONGER_APPLY, r.lapsed)
    steps = (CountLabel.STEP_1_TENTHS, CountLabel.STEP_2_TENTHS, CountLabel.STEP_3_TENTHS, CountLabel.STEP_4_TENTHS)
    for label, step in zip(steps, sink.order):
        emit(label, sink.tenths.get(step, 0))
    return 0


def cmd_dpapi_roundtrip(args):
    """Protect and unprotect a short made-up value with this Windows user's DPAPI, then flip one byte. Writes nothing."""
    from wholecount.session import dpapi

    data = b"wholecount dpapi check"
    blob = dpapi.protect(data)
    ok = dpapi.unprotect(blob) == data
    bad = bytearray(blob)
    bad[len(bad) // 2] ^= 0x01
    try:
        dpapi.unprotect(bytes(bad))
        detected = False
    except dpapi.DpapiError:
        detected = True
    emit(CountLabel.DPAPI_ROUND_TRIP, int(ok))
    emit(CountLabel.CHANGED_BYTE_DETECTED, int(detected))
    emit(CountLabel.FILES_WRITTEN, 0)
    return 0


_DEMO_ROWS = [list(r) for r in _R_ROWS]
_DEMO_ROWS[0][0] = "00123"
_DEMO_ROWS[5][2] = "Gíl"


def _demo_session(folder, state, practice=False, secret=None):
    """The made-up R and S fixture (with Fay Gíl and Client ID 00123) in a session, in its base or decided state."""
    import csv
    import json as _json
    import datetime as dt

    from wholecount.engine.geo.districts import DistrictIndex
    from wholecount.engine.geo.reference import ReferenceBackend
    from wholecount.session import commands as C
    from wholecount.session.runner import process
    from wholecount.session.state import Session

    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rows in (("R.csv", _DEMO_ROWS), ("S.csv", _S_ROWS)):
        path = folder / name
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(_R_HEADER)
            w.writerows(rows)
        paths.append(path)
    ref = ReferenceBackend.from_text("house_number,street,zip,borough,latitude,longitude\n"
                                     + "".join(",".join(map(str, p)) + "\n" for p in _R_POINTS), is_sample=practice)
    square = [[-74.0, 40.68], [-73.97, 40.68], [-73.97, 40.71], [-74.0, 40.71], [-74.0, 40.68]]
    gj = folder / "demo_districts.geojson"
    gj.write_text(_json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "senate_district": 26, "assembly_district": 52, "council_district": 33}, "geometry": {"type": "Polygon", "coordinates": [square]}}]}))
    if secret is None:
        import secrets
        from wholecount.session.secret_store import InstallSecret
        secret = InstallSecret(secrets.token_bytes(32))
    s = Session(secret, paths, backend=ref, districts=DistrictIndex.from_files([gj]), today=lambda: dt.date(2026, 10, 30),
                getuser=lambda: "demo", allow_sample=practice)
    process(s)

    def rk(cid):
        return min(k for k, r in s.results.rows.items() if r.value("Client_ID") == cid)

    def grp(kind):
        return next(g for g in s.results.groups if g.kind == kind)

    if state == "decided":
        for make in (lambda: C.KeepOneInCopyGroup(grp("identical").group_id, grp("identical").members[0]),
                     lambda: C.MarkNotCopies(grp("possible").group_id),
                     lambda: C.DecideSameIdConflict(grp("same_id_different").group_id, "approved_as_entered"),
                     lambda: C.AcceptFills([rk("R13")]), lambda: C.SetAsideRows([rk("R14")], "out_of_scope")):
            s.history.execute(make())
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    return s


def cmd_outputs_demo(args):
    """Write the made-up fixture's files: --state base|decided --out FOLDER [--map-points] [--exact-coordinates] [--practice]."""
    import tempfile

    from wholecount.engine.outputs.view import ExportSettings
    from wholecount.session.export import download

    out = pathlib.Path(_option(args, "--out") or tempfile.mkdtemp())
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        s = _demo_session(pathlib.Path(tmp), _option(args, "--state") or "base", "--practice" in args)
        fmts = {n: "xlsx" for n in ("Final_Clean_Mapped", "Unique_Clients", "Unique_Clients_By_Program", "Manual_Review_Needed",
                                    "Set_Aside_Records", "Map_Counts", "Map_Points")}
        settings = ExportSettings(formats=fmts, map_points="--map-points" in args, exact_coordinates="--exact-coordinates" in args)
        receipt = download(s, out, settings, overwrite=True, confirmed_synced=True)
    rows = {pathlib.Path(f.path).stem.replace("PRACTICE_", ""): f.rows for f in receipt.files}
    emit(CountLabel.CLEAN_ROWS, rows.get("Final_Clean_Mapped", 0))
    emit(CountLabel.REVIEW_ROWS, rows.get("Manual_Review_Needed", 0))
    emit(CountLabel.SET_ASIDE_ROWS, rows.get("Set_Aside_Records", 0))
    emit(CountLabel.UNIQUE_CLIENTS_ROWS, rows.get("Unique_Clients", 0))
    emit(CountLabel.BY_PROGRAM_ROWS, rows.get("Unique_Clients_By_Program", 0))
    emit(CountLabel.FILES_WRITTEN, len(receipt.files))
    return 0


def cmd_folder_check(args):
    """--path P: 1 when the folder is synced or on a network, else 0. Prints no path."""
    import os

    from wholecount.engine.outputs.folders import folder_warning

    emit(CountLabel.FOLDER_WARNING, int(folder_warning(_option(args, "--path") or "", os.environ) is not None))
    return 0


def _install_secret():
    from wholecount.session.secret_store import default_store, get_or_create_secret

    return get_or_create_secret(default_store())[0]


def cmd_corrections_demo(args):
    """--out FOLDER writes the base state's review file as Excel. --apply FILE reads a returned one and applies it."""
    from wholecount.engine.outputs.corrections_in import read_corrections
    from wholecount.engine.outputs.view import ExportSettings
    from wholecount.engine.read.reader import read_path
    from wholecount.session import commands as C
    from wholecount.session.export import build_view, download

    out = pathlib.Path(_option(args, "--out") or ".")
    s = _demo_session(out / "inputs", "base", secret=_install_secret())
    apply = _option(args, "--apply")
    if not apply:
        receipt = download(s, out, ExportSettings(formats={"Manual_Review_Needed": "xlsx"}), overwrite=True, confirmed_synced=True)
        emit(CountLabel.FILES_WRITTEN, len(receipt.files))
        return 0
    rf = read_path(pathlib.Path(apply))
    grid = rf.grids[0].rows
    read = read_corrections(grid, s.secret.mac, build_view(s), pathlib.Path(apply).name, rf.fingerprint)
    if read.accepted:
        s.history.execute(C.ApplyCorrections(read.accepted, rf.fingerprint, pathlib.Path(apply).name))
    emit(CountLabel.CORRECTIONS_ACCEPTED, len(read.accepted))
    emit(CountLabel.CORRECTIONS_REFUSED, len(read.refused))
    emit(CountLabel.REFUSED_OTHER_COLUMN, sum(1 for r in read.refused if r.code == "other_column_changed"))
    return 0


def cmd_saved_progress_demo(args):
    """Saved progress for the made-up decided state, with this user's DPAPI: --resume, --age-days N --purge, --clean."""
    import datetime as dt
    import json as _json
    import os

    from wholecount.paths import data_dir
    from wholecount.session.store import Store, snapshot
    from wholecount.session.resume import resume

    base = data_dir()
    store = Store(base)
    work = base / "saved_progress_demo_inputs"
    path = store.sessions / "demo.wcs"
    if "--clean" in args:
        if path.exists():
            path.unlink()
        emit(CountLabel.DELETED, 1)
        return 0
    if "--purge" in args:
        days = int(_option(args, "--age-days") or 0)
        if path.exists() and days:
            old = path.stat().st_mtime - days * 86400
            os.utime(path, (old, old))
        emit(CountLabel.DELETED, store.purge_expired(dt.datetime.now(dt.timezone.utc)))
        return 0
    secret = _install_secret()
    if "--resume" in args:
        saved = store.load(path)
        from wholecount.session.state import Session
        s = Session(secret, [], today=lambda: dt.date(2026, 10, 30), getuser=lambda: "demo")
        demo = _demo_session(work, "base", secret=secret)
        s.backend, s.districts = demo.backend, demo.districts
        plan = resume(s, saved, [work / "R.csv", work / "S.csv"])
        emit(CountLabel.DECISIONS_RESTORED, plan.kept)
        emit(CountLabel.NO_LONGER_APPLY, plan.lapsed)
        return 0
    s = _demo_session(work, "decided", secret=secret)
    store.save("demo", snapshot(s))
    data = store.load(path)
    text = _json.dumps(data)
    values = {v for row in _DEMO_ROWS + _S_ROWS for v in row[1:] if len(v) > 3} - {"Brooklyn", "Housing", "Youth", "Workforce"}
    emit(CountLabel.FILE_BYTES, path.stat().st_size)
    emit(CountLabel.DECRYPTS_FOR_THIS_USER, 1)
    emit(CountLabel.CELL_VALUES_FOUND, sum(1 for v in values if v in text))
    return 0


def cmd_backup_demo(args):
    """Back up a made-up secret in memory, check the known answer, restore it, and refuse a wrong passphrase and a changed
    byte. Writes nothing."""
    from wholecount.engine.secretbackup import BackupError, make_backup, read_backup

    secret, passphrase, salt = bytes(range(32)), "correct horse battery staple", bytes(range(16))
    known = ("57434231000102030405060708090a0b0c0d0e0f819956c362b0ba0d33e90b391c32960f1e927297476698fb8341002bde214ca8"
             "fc435e355253a2ec4c73060ea9261179f015affbf30b6c477b3938d53fbba454")
    blob = make_backup(secret, passphrase, salt)

    def refused(b, pw):
        try:
            read_backup(b, pw)
            return False
        except BackupError:
            return True
    bad = bytearray(blob)
    bad[30] ^= 1
    emit(CountLabel.BACKUP_BYTES, len(blob))
    emit(CountLabel.KNOWN_ANSWER_MATCHES, int(blob.hex() == known))
    emit(CountLabel.RESTORE_OK, int(read_backup(make_backup(secret, passphrase), passphrase) == secret))
    emit(CountLabel.WRONG_PASSPHRASE_REFUSED, int(refused(blob, passphrase + "x")))
    emit(CountLabel.ONE_CHANGED_BYTE_REFUSED, int(refused(bytes(bad), passphrase)))
    emit(CountLabel.FILES_WRITTEN, 0)
    return 0


def _cell_values(paths, default_glob):
    """Every cell value of four or more characters in the given CSV files (or the repo's made-up fixtures), to scan for."""
    import csv
    import pathlib

    files = [pathlib.Path(a) for a in paths] or sorted(pathlib.Path().glob(default_glob))
    out = set()
    for f in files:
        with open(f, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                out.update(v for k, v in row.items() if k != "Program" and v and len(v) >= 4)
    return out


def cmd_crosswalk_check(args):
    """Counts in this computer's crosswalk.db, whether any made-up cell value is in its bytes, and leftover journal files."""
    from wholecount.engine.crosswalk.store import CrosswalkStore
    from wholecount.paths import data_dir

    folder = data_dir()
    path = folder / "crosswalk.db"
    counts = (0, 0, 0, 0, 0)
    found = 0
    if path.exists():
        with CrosswalkStore.open(path, _install_secret().mac) as st:
            c = st.counts()
            counts = (c.people, c.person_keys, c.pair_verdicts, c.program_groups, c.merged)
        raw = path.read_bytes()
        found = sum(1 for v in _cell_values(args, "tests/fixtures/crosswalk/*.csv") if v.encode("utf-8") in raw)
    for label, n in zip((CountLabel.PEOPLE, CountLabel.PERSON_KEYS, CountLabel.PAIR_VERDICTS, CountLabel.PROGRAM_GROUPS,
                         CountLabel.MERGED), counts):
        emit(label, n)
    emit(CountLabel.CELL_VALUES_FOUND, found)
    emit(CountLabel.WAL_FILES, sum(1 for f in folder.glob("crosswalk.db-*")) if folder.exists() else 0)
    return 0


def cmd_calibration_check(args):
    """Labeled pairs in this computer's labeled.wcl, a scan of its contents for made-up cell values, and the regression check.
    --weights-change name=value re-scores with one weight changed."""
    from wholecount.engine.identity import load_settings
    from wholecount.paths import data_dir
    from wholecount.session import calibration as cs

    weights = dict(load_settings()["weights"])
    paths = []
    it = iter(args)
    for a in it:
        if a == "--weights-change":
            k, _, v = next(it).partition("=")
            weights[k] = int(v)
        else:
            paths.append(a)

    class _S:
        calibration_dir = data_dir() / "calibration"
        thresholds = None
    data = cs.load_labels(_S)
    pairs = len(data["pairs"]) if data else 0
    found = 0
    if data:
        text = repr(data)
        found = sum(1 for v in _cell_values(paths, "tests/fixtures/calibration/*.csv") if v in text)
    reg = cs.run_regression(_S, weights) if data else None
    emit(CountLabel.LABELED_PAIRS, pairs)
    emit(CountLabel.CELL_VALUES_FOUND, found)
    emit(CountLabel.REGRESSION_DROPPED, int(bool(reg and reg.dropped)))
    return 0


PERF_BACKENDS = ("geosupport", "reference", "none", "fake")
PERF_SUFFIXES = (".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json", ".xml")
PERF_SKIP = ("truth.json", "fake_gazetteer.csv")


def peak_memory_mb():
    """The process's peak memory. Windows: K32GetProcessMemoryInfo in kernel32, already on the guard's list. Linux:
    getrusage, which reports kilobytes."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        c = Counters()
        c.cb = ctypes.sizeof(c)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return int(c.PeakWorkingSetSize // (1024 * 1024))
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)


def _perf_backend(folder, fake):
    """(backend, word). --fake uses the set's fake_gazetteer.csv; otherwise whatever this computer has, as a real batch
    would: Geosupport, then a real reference file, then none."""
    import datetime as dt
    import os

    from wholecount.paths import data_dir

    if fake:
        from wholecount.engine.geo.fake import FakeGeoBackend

        return FakeGeoBackend(folder / "fake_gazetteer.csv"), "fake"
    from wholecount.engine.geo.backend import preflight

    b = preflight(os.environ, data_dir(), dt.date.today()).backend
    return b, {"geosupport": "geosupport", "reference": "reference"}.get(b.name, "none")


def _ms(start):
    import time

    return int(round((time.perf_counter() - start) * 1000))


def perf_run(folder, fake=False, stage_rounds=3):
    """Runs a set through the real session calls and jobs, and returns {label: int} plus the backend word. Nothing it
    prints holds a client value (H8). The download goes to a temporary folder that is removed."""
    import os
    import tempfile
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from wholecount.engine.progress import NullSink
    from wholecount.session import commands as C
    from wholecount.session.frame import export_settings, log_download, write_download
    from wholecount.session.runner import preview_counts
    from wholecount.session.secret_store import InstallSecret
    from wholecount.session.state import Session
    from wholecount.session.survey import survey
    from wholecount.ui.jobs.actions import AddFilesJob, ProcessJob

    folder = pathlib.Path(folder)
    backend, word = _perf_backend(folder, fake)
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in PERF_SUFFIXES and p.name not in PERF_SKIP)
    s = Session(InstallSecret(os.urandom(32)), (), backend=backend, getuser=lambda: "")
    out = {}

    def job(j):
        res = j.run(NullSink())
        s.history.execute(C.JobCommand(j, res))

    t = time.perf_counter()
    job(AddFilesJob(s, paths))
    out[CountLabel.ADD_FILES_MS] = _ms(t)
    # Include and match as a person would: the suggested header rows, and each proposed program group as one program.
    for tf in survey(s).tables:
        if tf.suggested_header_row and not tf.included:
            s.history.execute(C.SetupChange("tables", (tf.file_name, tf.idx, "header_row"), tf.suggested_header_row))
    for prop in survey(s).program_map.unconfirmed:
        s.history.execute(C.DecideProgramGroup("confirm", prop.members, prop.label))
    t = time.perf_counter()
    job(ProcessJob(s))
    out[CountLabel.PROCESS_MS] = _ms(t)
    t = time.perf_counter()
    preview_counts(s, [])
    out[CountLabel.PREVIEW_MS] = _ms(t)
    group = next((g for g in s.results.open_groups if g.kind == "identical"), None)
    if group is not None:
        t = time.perf_counter()
        s.history.execute(C.KeepOneInCopyGroup(group.group_id, min(group.members)))
        out[CountLabel.DECISION_MS] = _ms(t)
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    with tempfile.TemporaryDirectory() as tmp:
        t = time.perf_counter()
        log_download(s, write_download(s, pathlib.Path(tmp), export_settings(s)))
        out[CountLabel.DOWNLOAD_MS] = _ms(t)
    out[CountLabel.REDRAW_MAX_MS] = _redraw_max(s, stage_rounds)
    out[CountLabel.PEAK_MEMORY_MB] = peak_memory_mb()
    out[CountLabel.ROWS] = int(s.results.counts.received)
    out[CountLabel.FILES] = len(paths)
    return out, word


def _redraw_max(session, rounds):
    """Switches through all nine stages `rounds` times in the real window, offscreen, and keeps the slowest redraw."""
    import time

    from PySide6.QtWidgets import QApplication

    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.stages import STAGES
    from wholecount.ui.frame.window import MainWindow

    app = QApplication.instance() or QApplication([sys.argv[0]])
    w = MainWindow(SessionBridge(session, {"saved_progress": False, "reviewer_asked": True}))
    w.resize(1440, 900)
    w.show()
    app.processEvents()
    worst = 0
    for _ in range(rounds):
        for st in STAGES:
            t = time.perf_counter()
            w.go_to(st.id)
            app.processEvents()
            worst = max(worst, _ms(t))
    w.hide()          # not close(): closing asks the person first (A-16), and nobody is there to answer
    w.deleteLater()
    app.processEvents()
    return worst


def cmd_perf(args):
    """--set DIR [--fake] [--report PATH]: the performance run (SPEC 15). Counts-only output with integer labels, then the
    backend word. --report also writes the budget table that tools/perf_report.py writes."""
    folder, fake, report = None, False, None
    it = iter(args)
    for a in it:
        if a == "--set":
            folder = next(it)
        elif a == "--fake":
            fake = True
        elif a == "--report":
            report = next(it)
    if folder is None:
        print("usage: python -m wholecount.dev perf --set DIR [--fake] [--report PATH]", file=sys.stderr)
        return 2
    out, word = perf_run(folder, fake)
    for label, value in out.items():
        emit(label, value, grouped=False)
    assert word in PERF_BACKENDS
    print("backend " + word)
    if report:
        from tools import perf_report

        pathlib.Path(report).write_text(perf_report.render({k.value: v for k, v in out.items()}, word), encoding="utf-8")
    return 0


COMMANDS = {"perf": cmd_perf, "check": cmd_check, "read": cmd_read, "secret": cmd_secret, "columns": cmd_columns, "tidy": cmd_tidy,
            "standardize": cmd_standardize, "geo-status": cmd_geo_status, "geo-check": cmd_geo_check,
            "offset-demo": cmd_offset_demo, "map-demo": cmd_map_demo, "people-demo": cmd_people_demo,
            "people-check": cmd_people_check, "programs-demo": cmd_programs_demo, "programs-check": cmd_programs_check,
            "session-demo": cmd_session_demo, "session-check": cmd_session_check, "dpapi-roundtrip": cmd_dpapi_roundtrip,
            "outputs-demo": cmd_outputs_demo, "folder-check": cmd_folder_check, "corrections-demo": cmd_corrections_demo,
            "saved-progress-demo": cmd_saved_progress_demo, "backup-demo": cmd_backup_demo,
            "crosswalk-check": cmd_crosswalk_check, "calibration-check": cmd_calibration_check}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print("usage: python -m wholecount.dev {" + ",".join(sorted(COMMANDS)) + "}", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
