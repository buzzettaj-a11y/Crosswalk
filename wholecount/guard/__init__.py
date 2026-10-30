"""Offline guard: the fail-closed audit hook that denies network, process and foreign-code events (SPEC 12)."""

from . import offline_guard
from .config import DPAPI_DLL_NAMES, DPAPI_SYMBOLS, GEOSUPPORT_SYMBOLS
from .offline_guard import OfflineImportViolation, OfflineViolation, allow_open_file, install

__all__ = ["install", "install_for_app", "allow_open_file", "OfflineViolation", "OfflineImportViolation", "INSTALLED"]


def install_for_app(geosupport_dirs=(), log=None):
    """Install the guard with the app's allowlists merged in. Returns the list of violations, which grows as events are denied."""
    return install(
        allowed_dll_prefixes=tuple(geosupport_dirs),
        allowed_dll_names=DPAPI_DLL_NAMES,
        allowed_symbols=DPAPI_SYMBOLS + GEOSUPPORT_SYMBOLS,
        log=log,
    )


def __getattr__(name):
    # INSTALLED is read live from the hook module, so it is never a stale copy.
    if name == "INSTALLED":
        return offline_guard.INSTALLED
    raise AttributeError(name)
