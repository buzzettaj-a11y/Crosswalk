"""Starting the window (SPEC 11.1). The guard is already installed by __main__ before this module is imported."""
import datetime as dt
import platform
import sys


def _guard_installed():
    from wholecount import guard

    return bool(guard.INSTALLED)


def _store_ok(store):
    try:
        store.base.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def _dpapi_ok():
    from wholecount.session import dpapi

    try:
        return dpapi.unprotect(dpapi.protect(b"check")) == b"check"
    except Exception:  # noqa: BLE001  any failure reads as not available
        return False


def build(argv=None):
    """The QApplication, session, bridge and window, ready to show. Returns (app, window)."""
    from PySide6.QtWidgets import QApplication

    from wholecount.paths import data_dir
    from wholecount.session.secret_store import SecretUnreadable, default_store, get_or_create_secret
    from wholecount.session.state import Session
    from wholecount.session.store import Store
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow
    from wholecount.ui.theme import apply

    # Only the program name reaches Qt, so no Qt switch can arrive on the command line (research 3.3).
    app = QApplication.instance() or QApplication([sys.argv[0]])
    from wholecount import crash

    crash.install()              # M14: one box with the error code; nothing logged to disk (A-15)
    apply.apply_theme(app)
    secret_ok = True
    try:
        secret, _ = get_or_create_secret(default_store())
    except SecretUnreadable:
        from wholecount.session.secret_store import InstallSecret

        secret_ok = False
        secret = InstallSecret(bytes(32))     # a stand-in so the window opens; the system check says the key won't open
    session = Session(secret)
    store = Store(data_dir())
    if secret_ok:
        # M13: the saved crosswalk is on exactly when this file exists; the calibration files and the lines live beside it.
        session.crosswalk_path = data_dir() / "crosswalk.db"
        session.calibration_dir = data_dir() / "calibration"
        lines = store.prefs().get("thresholds")
        if lines:
            session.thresholds = (int(lines["possible_min"]), int(lines["likely_min"]))
    saved = bool(store.prefs().get("saved_progress", True))
    # With an unreadable key file nothing is saved, because keys made now wouldn't match the real ones.
    session.store = store if saved and secret_ok else None
    preflight = session.preflight()
    ui = {"saved_progress": saved, "font_ok": all(apply.FONT_STATUS.values()), "secret_ok": secret_ok,
          "store_ok": _store_ok(store), "dpapi_ok": _dpapi_ok(), "guard_ok": _guard_installed(),
          "windows": f"{platform.system()} {platform.release()}"}
    bridge = SessionBridge(session, ui, preflight, clock=lambda: dt.datetime.now(dt.timezone.utc))
    bridge.secret_store = default_store() if secret_ok else None
    bridge.prefs_store = store
    window = MainWindow(bridge)
    return app, window


def run(argv=None):
    app, window = build(argv)
    window.show()
    return app.exec()
