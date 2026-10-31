"""Errors that never carry client values (A-15, H8). The message names the error's class, module and line, never str(exc),
the traceback text or locals. No file is written. This is the package's only sys.excepthook; M10 and M14 extend it."""
import sys
import traceback

from wholecount import copy


def safe_error_text(exc):
    tb = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
    last = tb[-1] if tb else None
    module = type(exc).__module__
    if last is not None:
        module = last.filename.replace("\\", "/").rsplit("/", 1)[-1]
    return copy.get("errors.safe_text", kind=type(exc).__name__, module=module, line=last.lineno if last else 0)


_HANDLERS = []          # M14: crash.py adds the window's message box here. Each gets the exception and returns nothing.


def add_handler(fn):
    if fn not in _HANDLERS:
        _HANDLERS.append(fn)


def _hook(exc_type, exc, tb):
    if exc is not None and exc.__traceback__ is None:
        exc.__traceback__ = tb
    if sys.__stderr__ is not None:          # None in a windowed exe (console=False)
        sys.__stderr__.write(safe_error_text(exc) + "\n")
    for fn in list(_HANDLERS):
        try:
            fn(exc)
        except Exception:  # noqa: BLE001  a failing handler must never hide the first fault
            pass


def install_excepthook():
    sys.excepthook = _hook
    return _hook
