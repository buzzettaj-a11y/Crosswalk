"""Offline guard: the fail-closed audit hook that denies network, process and foreign-code events (SPEC 12)."""

import os

from . import offline_guard
from .config import DPAPI_DLL_NAMES, DPAPI_SYMBOLS, GEOSUPPORT_SYMBOLS, discover_geosupport_dirs
from .offline_guard import OfflineImportViolation, OfflineViolation, allow_open_file, install

__all__ = ["install", "install_for_app", "allow_open_file", "OfflineViolation", "OfflineImportViolation", "INSTALLED"]


def install_for_app(geosupport_dirs=None, log=None):
    """Install the guard with the app's allowlists merged in. Returns the list of violations, which grows as events are denied.
    With no folders passed, it finds the Geosupport install itself, so it stays the first statement of __main__ and dev."""
    global _APP_VIOLATIONS
    # Idempotent (M14): the frozen app installs it from the runtime hook and again from __main__. A second call adds no
    # second audit hook and returns the first call's violation list.
    if _APP_VIOLATIONS is not None and offline_guard.INSTALLED:
        return _APP_VIOLATIONS
    if geosupport_dirs is None:
        geosupport_dirs = discover_geosupport_dirs(os.environ, os.path.isdir)
    _APP_VIOLATIONS = install(
        allowed_dll_prefixes=tuple(geosupport_dirs),
        allowed_dll_names=DPAPI_DLL_NAMES,
        allowed_symbols=DPAPI_SYMBOLS + GEOSUPPORT_SYMBOLS,
        log=log,
    )
    return _APP_VIOLATIONS


_APP_VIOLATIONS = None


def __getattr__(name):
    # INSTALLED is read live from the hook module, so it is never a stale copy.
    if name == "INSTALLED":
        return offline_guard.INSTALLED
    raise AttributeError(name)
