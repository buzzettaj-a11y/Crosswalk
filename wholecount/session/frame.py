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
