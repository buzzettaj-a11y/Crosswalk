"""Accessibility (SPEC 11.3, H14). announce() updates a hidden live-region label and sends a name-changed event. It's called
when a step begins and when a job ends or fails, never on every count."""
from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QLabel

ANNOUNCED = []                            # what was announced, for tests; in memory only


class LiveRegion(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("liveRegion")
        self.setFixedSize(1, 1)
        self.setText("")
        self.move(-10, -10)


_region = None


def install(parent):
    global _region
    _region = LiveRegion(parent)
    return _region


def announce(text):
    ANNOUNCED.append(text)
    if _region is None:
        return
    try:
        _region.setAccessibleName(text)
        QAccessible.updateAccessibility(QAccessibleEvent(_region, QAccessible.NameChanged))
    except RuntimeError:
        pass
