"""The source mark: a 14px ink square holding the file letter, drawn before a file name (style guide)."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from wholecount.ui.theme import color


class SourceMark(QWidget):
    def __init__(self, letter, parent=None):
        super().__init__(parent)
        self.letter = letter
        self.setFixedSize(14, 14)
        self.setAccessibleName(letter)

    def sizeHint(self):
        return QSize(14, 14)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(color("ink")))
        f = QFont(self.font())
        f.setPixelSize(9)
        f.setWeight(QFont.ExtraBold)
        p.setFont(f)
        p.setPen(QColor(color("on-dark")))
        p.drawText(QRectF(self.rect()), Qt.AlignCenter, self.letter)
        p.end()
