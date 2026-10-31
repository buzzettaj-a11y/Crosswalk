"""PageBar (M12 section 0): Prev, Page {n} of {m}, Next and a page size select. It never holds row data."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from wholecount import copy
from wholecount.ui.widgets.style import button, hbox, label, narrow_combo

SIZES = (50, 100, 250)


class PageBar(QWidget):
    page_changed = Signal(int)
    size_changed = Signal(int)

    def __init__(self, page=0, pages=1, size=50, sizes=SIZES, parent=None):
        super().__init__(parent)
        lay = hbox(self, spacing=8)
        self.prev = button(copy.get("grid.prev"), "quiet", "nav", name="pagePrev")
        self.where = label("", role="caption", name="pageWhere")
        self.next = button(copy.get("grid.next"), "quiet", "nav", name="pageNext")
        self.size = QComboBox()
        narrow_combo(self.size, 6)
        self.size.setObjectName("pageSize")
        for n in sizes:
            self.size.addItem(copy.get("grid.page_size", n=n), n)
        self.size.setCurrentIndex(max(0, self.size.findData(size)))
        for w in (self.prev, self.where, self.next, self.size):
            lay.addWidget(w)
        lay.addStretch(1)
        self.page, self.pages = page, pages
        self.prev.clicked.connect(lambda: self.go(self.page - 1))
        self.next.clicked.connect(lambda: self.go(self.page + 1))
        self.size.activated.connect(lambda _: self.size_changed.emit(self.size.currentData()))
        self.set_pages(page, pages)

    def set_pages(self, page, pages):
        self.page, self.pages = page, max(1, pages)
        self.where.setText(copy.get("grid.page_of", page=self.page + 1, pages=self.pages))
        self.prev.setVisible(self.page > 0)
        self.next.setVisible(self.page < self.pages - 1)

    def go(self, page):
        page = max(0, min(page, self.pages - 1))
        if page != self.page:
            self.set_pages(page, self.pages)
            self.page_changed.emit(page)
