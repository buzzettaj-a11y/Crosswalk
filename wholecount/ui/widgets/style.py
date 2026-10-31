"""Styling helpers. Widgets get styled through dynamic properties the QSS matches, never inline colors (SPEC 11.2)."""
from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout

from wholecount import copy


def set_prop(widget, name, value):
    """Set a dynamic property and re-polish, so the QSS rule for the new value applies at once."""
    widget.setProperty(name, value)
    st = widget.style()
    st.unpolish(widget)
    st.polish(widget)
    widget.update()


# Letter spacing from tokens.json, in em. QSS has no letter-spacing, so it goes on the font.
SPACING = {"kicker": 0.14, "strip-kicker": 0.1, "tag": 0.1, "column-head": 0.06, "ledger-kicker": 0.14, "band-kicker": 0.1,
           "wordmark": 0.06}
TABULAR = {"count-lg", "count", "count-row", "ticker", "band-line"}


def _font_for(w, role):
    f = QFont(w.font())
    if role in SPACING:
        f.setLetterSpacing(QFont.PercentageSpacing, 100 + SPACING[role] * 100)
    if role in TABULAR and hasattr(QFont, "Tag"):
        try:
            f.setFeature(QFont.Tag("tnum"), 1)
        except (AttributeError, TypeError):
            pass
    w.setFont(f)


def label(text="", role="body", tone=None, wrap=False, name=None):
    w = QLabel(text)
    w.setTextFormat(Qt.PlainText)
    set_prop(w, "role", role)
    _font_for(w, role)
    if tone:
        set_prop(w, "tone", tone)
    w.setWordWrap(wrap)
    if name:
        w.setObjectName(name)
    return w


def text(key, **params):
    return copy.get(key, **params)


def button(text_, kind="secondary", tone=None, name=None):
    b = QPushButton(text_)
    set_prop(b, "kind", kind)
    if tone:
        set_prop(b, "tone", tone)
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.StrongFocus)
    if name:
        b.setObjectName(name)
    return b


def narrow_combo(cb, chars=8):
    """A combo box that never forces the page wider than the window: it sizes to a few characters, not its longest item."""
    from PySide6.QtWidgets import QComboBox

    cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cb.setMinimumContentsLength(chars)
    return cb


def rule():
    f = QFrame()
    f.setObjectName("rule")
    f.setFixedHeight(1)
    return f


def vbox(parent=None, margins=(0, 0, 0, 0), spacing=0):
    lay = QVBoxLayout(parent)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def hbox(parent=None, margins=(0, 0, 0, 0), spacing=0):
    lay = QHBoxLayout(parent)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear(item.layout())


class WrapScroll(QScrollArea):
    """A vertical scroll area that gives its widget the height its wrapped labels need at the current width. QScrollArea
    on its own sizes by sizeHint, which ignores height-for-width, so wrapped text would overlap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)

    def setWidget(self, w):
        super().setWidget(w)
        w.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.widget() and ev.type() == QEvent.LayoutRequest:
            self.fit()
        return False

    def fit(self):
        w = self.widget()
        if w is None or w.layout() is None:
            return
        need = w.layout().totalHeightForWidth(self.viewport().width())
        if need > 0:
            w.setMinimumHeight(need)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.fit()


class WrapButton(QPushButton):
    """A quiet link button whose text wraps, for narrow columns. The label inside ignores the mouse, so the button gets
    every click, keeps its focus outline, and its accessible name is the full text."""

    def __init__(self, text_="", kind="quiet", tone="nav", name=None):
        super().__init__()
        set_prop(self, "kind", kind)
        set_prop(self, "tone", tone)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        if name:
            self.setObjectName(name)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        self.inner = QLabel()
        self.inner.setWordWrap(True)
        self.inner.setAttribute(Qt.WA_TransparentForMouseEvents)
        set_prop(self.inner, "role", "link")
        lay.addWidget(self.inner)
        self.setText(text_)

    def setText(self, t):
        self.inner.setText(t)
        self.setAccessibleName(t)
        self.updateGeometry()

    def text(self):
        return self.inner.text()

    def set_tone(self, tone):
        set_prop(self, "tone", tone)
        set_prop(self.inner, "tone", "amber" if tone == "amber" else "blue")

    def sizeHint(self):
        h = self.inner.heightForWidth(max(60, self.width() - 8)) if self.width() > 20 else self.inner.sizeHint().height()
        return QSize(super().sizeHint().width(), max(36, h + 16))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return max(36, self.inner.heightForWidth(max(60, w - 8)) + 16)
