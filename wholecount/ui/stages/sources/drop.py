"""Drag and drop (A-18). Only this stage's body takes dropped files, and only local files. Everywhere else in the window a
drop is refused before it lands, so a text field never receives a dropped path as text."""
import pathlib
import sys

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

ACCEPTED = (".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".json", ".xml")
RUN_LOG = []                              # in memory only: why network drive detection was skipped


def dropped_paths(mime):
    """(paths, problem): problem is None, "not_local" or "network_address"."""
    if mime is None or not mime.hasUrls():
        return [], "not_local"
    paths = []
    for url in mime.urls():
        local = url.toLocalFile()
        if not local:
            return [], "not_local"
        if local.startswith("\\\\") or local.startswith("//"):
            return [], "network_address"
        p = pathlib.Path(local)
        if p.is_dir() or not p.is_file():
            return [], "not_local"
        paths.append(p)
    return paths, None if paths else "not_local"


def on_network_drive(path):
    """True for a file on a mapped network drive (SPEC 12.6). kernel32 is already on the guard's allowlist."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        root = str(pathlib.Path(path).anchor)
        return ctypes.windll.kernel32.GetDriveTypeW(root) == 4      # DRIVE_REMOTE
    except Exception:  # noqa: BLE001  detection not possible: show nothing and log the choice
        RUN_LOG.append(("drive_type_unknown",))
        return False


_GUARD = None
DRAG_EVENTS = (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop)


def guard():
    """The one application-wide drop filter, installed once however many windows there are."""
    global _GUARD
    from PySide6.QtWidgets import QApplication

    if _GUARD is None:
        _GUARD = DropGuard()
        QApplication.instance().installEventFilter(_GUARD)
    return _GUARD


class DropGuard(QObject):
    """Application filter: drag events reach only widgets inside a registered drop target."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []

    def add(self, widget):
        self.targets.append(widget)

    def _inside(self, w):
        alive = []
        for t in self.targets:
            try:
                t.isVisible()
                alive.append(t)
            except RuntimeError:
                continue
        self.targets = alive
        return isinstance(w, QWidget) and any(t is w or t.isAncestorOf(w) for t in self.targets)

    def eventFilter(self, obj, ev):
        if ev.type() in DRAG_EVENTS and isinstance(obj, QWidget):
            if not self._inside(obj):
                ev.ignore()
                return True
        return False
