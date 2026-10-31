"""What the window's frame reads from the session (SPEC 3.2, 11.3). The UI never imports the engine, so the engine's
numbers, equations and sentences reach FrameView through these functions. Nothing here works out a rule."""
from wholecount.engine.counts import BalanceError, Locations, assert_balance, ledger_lines  # noqa: F401
from wholecount.engine.outputs.summary_doc import confidence_reason  # noqa: F401


def balance_ok(results):
    try:
        assert_balance(results.balance, results.outcomes.values())
    except BalanceError:
        return False
    return True


def lines(results):
    return ledger_lines(results.balance, results.counts.locations)


def default_field_keys():
    from wholecount.engine.schema import default_schema

    return {f.key for f in default_schema().enabled_fields()}


def files_ready(practice):
    """How many files a download would write with the default settings (OUT-1)."""
    from types import SimpleNamespace

    from wholecount.engine.outputs.view import ExportSettings
    from wholecount.engine.outputs.writer import files_to_write

    return len(files_to_write(SimpleNamespace(practice=practice), ExportSettings()))


def sample_backend():
    """The sample address reference beside the example files (P-GEO-4a). Only Try example data uses it."""
    import pathlib

    from wholecount.engine.geo.reference import ReferenceBackend

    return ReferenceBackend.from_path(pathlib.Path(__file__).resolve().parents[1] / "sample_data" / "sample_reference.csv")


CORRECTIONS_HEADER = {"Record_Key", "Run_ID", "Signature"}


def corrections_files(load):
    """Names of loaded files that are a Manual_Review_Needed file sent back: a table whose header has Record_Key, Run_ID
    and Signature. They are corrections, never a source (SPEC 9.3)."""
    letters = {t.letter for t in load.tables if CORRECTIONS_HEADER <= set(t.headers)}
    return [o.name for o in load.files if o.letter in letters]


def backend_kind(backend):
    """Which pre-run backend line applies: geosupport, reference, practice or none (P-GEO-4). From the backend itself."""
    name = getattr(backend, "name", "none")
    return {"geosupport": "geosupport", "reference": "reference", "reference_sample": "practice"}.get(name, "none")


def stale_reason(session):
    """The earliest out-of-date node, for the Process line `Out of date. {what changed}.`"""
    from wholecount.session import staleness

    return staleness.earliest(session.stale)


def extra_geo_fields():
    """The extra Geosupport fields M05's GeoOptions lists (only census tract today)."""
    from wholecount.engine.geo.backend import GeoOptions

    return tuple(getattr(GeoOptions, "AVAILABLE", ("census_tract",)))


def export_settings(session):
    """ExportSettings from the set-up's export_settings section: formats, columns off, Map_Points, exact coordinates."""
    from wholecount.engine.outputs.view import ExportSettings

    if session is None:
        return ExportSettings()
    from wholecount.engine.outputs.columns import FileId

    sec = dict(session.setup.sections.get("export_settings", {}))
    known = {k: sec[k] for k in ("formats", "map_points", "exact_coordinates", "include_file_names") if k in sec}
    # Stored by file name so saved progress holds plain text; the writer wants FileId keys.
    off = {FileId(k): frozenset(v) for k, v in dict(sec.get("columns_off", {})).items()}
    return ExportSettings(columns_off=off, **known)


def summary_html(session, include_file_names):
    """M09's printable page as HTML, from the same SummaryDoc the PDF draws (A-03)."""
    from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
    from wholecount.session.export import build_view

    return render_summary_html(build_summary(build_view(session), include_file_names))


def write_reason(exc):
    """One of four fixed reasons a file could not be written. The OS message is never shown: it can hold a path."""
    import errno

    if getattr(exc, "winerror", None) in (32, 33):
        return "in_use"
    if getattr(exc, "errno", None) == errno.ENOSPC:
        return "disk_full"
    if isinstance(exc, PermissionError):
        return "refused"
    return "failed"


def receipt_text(receipt):
    from wholecount.engine.outputs.receipt import receipt_text as text

    return text(receipt)


def folder_warning(path):
    import os

    from wholecount.engine.outputs.folders import folder_warning as warn

    return warn(str(path), os.environ)


def existing_names(session, folder, settings):
    import pathlib

    from wholecount.engine.outputs import writer
    from wholecount.session.export import build_view

    view = build_view(session, settings)
    names = [writer.file_name(f, view, settings) for f in writer.files_to_write(view, settings)]
    return [n for n in names if (pathlib.Path(folder) / n).exists()]


def data_file_ids():
    """The data files whose format the operator picks (the logs and quality report have fixed formats)."""
    from wholecount.engine.outputs.columns import LOG_FILES, TABLE_FILES, FileId

    return tuple(f.value for f in TABLE_FILES if f not in LOG_FILES and f != FileId.DATA_QUALITY_REPORT)


def clean_file_id():
    return "Final_Clean_Mapped"


def planned_file_count(session, settings):
    from wholecount.engine.outputs import writer
    from wholecount.session.export import build_view

    return len(writer.files_to_write(build_view(session, settings), settings))


def write_download(session, folder, settings, environ=None):
    """Every file through the writer (temporary names, then a rename). Returns the Receipt."""
    from wholecount.engine.outputs import writer
    from wholecount.session.export import build_view

    return writer.write_outputs(build_view(session, settings), folder, settings, session.clock, confirmed_synced=True,
                                overwrite=True, environ=environ)


def log_download(session, receipt):
    import pathlib

    from wholecount.engine.outputs.audit_entry import entry

    session.log(entry("DOWNLOAD", file_name=[pathlib.Path(f.path).name for f in receipt.files], count=len(receipt.files),
                      reviewer=session.reviewer or None))
