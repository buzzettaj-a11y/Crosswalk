"""The guard's DENY_MODULES and offline_rules.FORBIDDEN_MODULES describe the same thing from two places, on purpose (research 8.3).
Drift in either list fails here until a reviewer updates the other or the exception set below."""
from tools.offline_rules import FORBIDDEN_MODULES
from wholecount.guard.offline_guard import DENY_MODULES

# Forbidden in the build and the source, but not denied at runtime by the guard.
FORBIDDEN_BUT_NOT_DENIED = frozenset({
    # The build excludes multiprocessing (PyInstaller's runtime hook imports it and pulls in socket, research R4 notes).
    # At runtime its socket use is still caught by the socket deny, so the guard need not refuse the import.
    "multiprocessing", "_multiprocessing",
    # Qt modules that ship only in PySide6-Addons, which the lock forbids. The build gate catches them as well (research R4).
    "PySide6.QtWebEngineQuick", "PySide6.QtPositioning", "PySide6.QtHttpServer", "PySide6.QtNetworkAuth",
})

# Denied at runtime by the guard, but not listed in FORBIDDEN_MODULES (parents, aliases and version-specific names).
DENIED_BUT_NOT_FORBIDDEN = frozenset({
    "http", "xmlrpc",                                   # parent packages; FORBIDDEN_MODULES names their client and server modules
    "_xxinterpchannels", "_xxinterpqueues",             # 3.12 spellings of the sub-interpreter channel and queue modules
    "interpreters", "concurrent.interpreters",          # the public sub-interpreter modules (PEP 734)
    "websocket",                                        # websocket-client's import name
})


def test_forbidden_minus_denied_is_the_pinned_exception_set():
    assert FORBIDDEN_MODULES - DENY_MODULES == FORBIDDEN_BUT_NOT_DENIED


def test_denied_minus_forbidden_is_the_pinned_exception_set():
    assert DENY_MODULES - FORBIDDEN_MODULES == DENIED_BUT_NOT_FORBIDDEN
