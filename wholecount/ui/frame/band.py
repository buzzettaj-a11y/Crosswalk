"""The ledger band (narrow mode): 44px, four groups and a Details link. Text is elided, never wrapped."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QWidget

from wholecount import copy
from wholecount.ui.widgets.style import button, hbox, label, vbox

HEIGHT = 44


class _Group(QWidget):
    def __init__(self, kicker_key, blue=False, parent=None):
        super().__init__(parent)
        lay = vbox(self, (14, 4, 14, 4), 1)
        self.kicker = label(copy.get(kicker_key), role="band-kicker", tone="blue" if blue else None)
        self.line = label("", role="band-line")
        lay.addWidget(self.kicker)
        lay.addWidget(self.line)
        self.full = ""

    def set_text(self, text):
        self.full = text
        self.line.setToolTip(text)
        self._elide()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._elide()

    def _elide(self):
        self.line.setText(self.line.fontMetrics().elidedText(self.full, Qt.ElideRight, max(20, self.width() - 28)))


def band_texts(v):
    """The four lines, each a short pre-run phrase until the run has numbers."""
    batch = (copy.get("band.batch.line", rows=v.rows_in, files=v.files) if v.rows_in else
             copy.get("band.batch.before"))
    c = v.counts
    if c is None or v.running or v.results_stale or not c.balance_ok:
        standing = copy.get("band.standing.before") if not v.results_stale else copy.get("band.counts.stale")
        counts = copy.get("band.counts.before") if not v.results_stale else copy.get("band.counts.stale")
        located = copy.get("band.located.before") if not v.results_stale else copy.get("band.counts.stale")
        return batch, standing, counts, located
    standing = copy.get("band.standing.line", counted=c.counted, not_yet=c.not_counted_yet, aside=c.set_aside)
    if c.goal1[0] == c.goal1[1]:
        counts = copy.get("band.counts.line", g1=c.goal1[0], g2=c.goal2[0])
    else:
        counts = copy.get("band.counts.line_range", g1=c.goal1[0], g1hi=c.goal1[1], g2=c.goal2[0])
    loc = c.locations
    located = copy.get("band.located.line", high=loc.high, low=loc.low, not_mapped=loc.not_mapped)
    return batch, standing, counts, located


class LedgerBand(QFrame):
    details = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("band")
        self.setFixedHeight(HEIGHT)
        lay = hbox(self, (6, 0, 14, 0), 0)
        self.groups = [_Group("band.kicker.batch"), _Group("band.kicker.standing"), _Group("band.kicker.counts", blue=True),
                       _Group("band.kicker.located")]
        for i, g in enumerate(self.groups):
            if i:
                div = QFrame()
                div.setObjectName("rule")
                div.setFixedWidth(1)
                div.setFixedHeight(28)
                lay.addWidget(div, 0, Qt.AlignVCenter)
            lay.addWidget(g, 1)
        self.details_button = button(copy.get("band.details"), "quiet", "nav", name="detailsLink")
        self.details_button.clicked.connect(self.details)
        lay.addWidget(self.details_button, 0, Qt.AlignVCenter)

    def update_view(self, v):
        for g, t in zip(self.groups, band_texts(v)):
            g.set_text(t)
