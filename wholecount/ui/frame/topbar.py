"""The top bar (SPEC 11.3): the mark, the wordmark, PRACTICE when it applies, and the status line.

Under 1360 wide it also shows Close Wholecount, and Offline becomes the full trust statement (A-23)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QWidget

from wholecount import brand, copy
from wholecount.ui.theme import color
from wholecount.ui.widgets.style import button, hbox, label
from wholecount.ui.widgets.tag import tag

HEIGHT = 48


class _Square(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(color("blue-500")))
        p.end()


def backend_text(view):
    """(text, old suffix or "") from the preflight's backend."""
    if view.backend == "geosupport":
        return (copy.get("top.backend.geosupport", release=view.release),
                copy.get("top.backend.geosupport_old") if view.release_stale else "")
    if view.backend == "reference":
        return copy.get("top.backend.reference"), ""
    if view.backend == "reference_sample":
        return copy.get("top.backend.sample"), ""
    return copy.get("top.backend.none"), ""


def saved_text(view, now):
    if not view.saved_progress:
        return copy.get("top.saved.off")
    if view.saved_at is None:
        return copy.get("top.saved.nothing")
    secs = max(0, int((now - view.saved_at).total_seconds()))
    if secs < 60:
        return copy.get("top.saved.just_now")
    if secs < 3600:
        return copy.get("top.saved.minutes", n=secs // 60)
    return copy.get("top.saved.hours", n=secs // 3600)


class TopBar(QFrame):
    def __init__(self, on_close, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(HEIGHT)
        lay = hbox(self, (20, 0, 20, 0), 10)
        lay.addWidget(_Square(), 0, Qt.AlignVCenter)
        self.wordmark = label(brand.PRODUCT_NAME.upper(), role="wordmark", name="wordmark")
        lay.addWidget(self.wordmark, 0, Qt.AlignVCenter)
        self.practice = tag(copy.get("top.practice"), "practice")
        self.practice.setObjectName("practiceTag")
        lay.addWidget(self.practice, 0, Qt.AlignVCenter)
        lay.addStretch(1)
        self.offline = label("", role="status", name="topOffline")
        self.backend = label("", role="status", name="topBackend")
        self.backend_old = label("", role="status", tone="amber", name="topBackendOld")
        self.saved = label("", role="status", name="topSaved")
        for i, w in enumerate((self.offline, self.backend, self.backend_old, self.saved)):
            if i in (1, 3):
                lay.addWidget(label("·", role="status"), 0, Qt.AlignVCenter)
            lay.addWidget(w, 0, Qt.AlignVCenter)
        self.close_button = button(copy.get("top.close"), "quiet", "dark", name="topClose")
        self.close_button.clicked.connect(on_close)
        lay.addSpacing(8)
        lay.addWidget(self.close_button, 0, Qt.AlignVCenter)
        self.compact = False

    def set_compact(self, compact):
        self.compact = compact
        self.close_button.setVisible(compact)
        self.offline.setText(copy.get("top.offline_narrow" if compact else "top.offline"))

    def update_view(self, view, now):
        self.practice.setVisible(view.practice)
        self.offline.setText(copy.get("top.offline_narrow" if self.compact else "top.offline"))
        text, old = backend_text(view)
        self.backend.setText(text)
        self.backend_old.setText(old)
        self.backend_old.setVisible(bool(old))
        self.saved.setText(saved_text(view, now or view.now))
