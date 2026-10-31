"""HBar and BarRow (M12 section 0): a 6px bar on a line-soft track, and a label, bar and right-aligned figure."""
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from wholecount.ui.theme import color
from wholecount.ui.widgets.style import hbox, label

TONE_COLOR = {"ink-2": "ink-2", "amber": "amber-500", "blue": "blue-500"}


class HBar(QWidget):
    def __init__(self, fraction, tone="ink-2", outline=False, parent=None):
        super().__init__(parent)
        self.fraction = max(0.0, min(1.0, float(fraction)))
        self.tone = tone
        self.outline = outline
        self.setFixedHeight(6)

    def sizeHint(self):
        return QSize(160, 6)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(color("line-soft")))
        w = int(self.width() * self.fraction)
        c = QColor(color(TONE_COLOR[self.tone]))
        if w:
            if self.outline:
                p.setPen(c)
                p.drawRect(0, 0, max(0, w - 1), self.height() - 1)
            else:
                p.fillRect(0, 0, w, self.height(), c)
        p.end()


class BarRow(QWidget):
    def __init__(self, text, value, fraction, tone="ink-2", outline=False, parent=None):
        super().__init__(parent)
        lay = hbox(self, spacing=10)
        self.name = label(text, role="note")
        self.bar = HBar(fraction, tone, outline)
        self.value = label(f"{value:,}", role="row-title")
        lay.addWidget(self.name, 2)
        lay.addWidget(self.bar, 3)
        lay.addWidget(self.value)
        self.bar.setAccessibleName(f"{text}, {value:,}")
