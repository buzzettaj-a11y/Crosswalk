"""GridView (M11 section 0): a table over a QAbstractTableModel that keeps its scroll offsets and page across a model reset.
State is held by the window, keyed by (stage ID, grid ID). The grid scrolls on its own; the page never does."""
from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QHeaderView, QTableView, QWidget

from wholecount import copy
from wholecount.ui.widgets.style import button, hbox, label, set_prop, vbox

PAGE_SIZES = (50, 100, 250)
ROW_HEIGHT = 36


@dataclass
class GridState:
    v: int = 0
    h: int = 0
    page: int = 0
    page_size: int = 50
    sort: tuple = (None, Qt.AscendingOrder)


class RowsModel(QAbstractTableModel):
    """Headers and rows of text, one page at a time. Sorting is by a header click, through the model."""

    def __init__(self, headers=(), rows=(), numeric=frozenset(), parent=None):
        super().__init__(parent)
        self.headers = list(headers)
        self.all_rows = [list(r) for r in rows]
        self.numeric = set(numeric)
        self.page = 0
        self.page_size = PAGE_SIZES[0]
        self._order = list(range(len(self.all_rows)))

    def set_data(self, headers, rows):
        self.beginResetModel()
        self.headers = list(headers)
        self.all_rows = [list(r) for r in rows]
        self._order = list(range(len(self.all_rows)))
        self.endResetModel()

    @property
    def pages(self):
        return max(1, -(-len(self.all_rows) // self.page_size))

    def set_page(self, page, size=None):
        self.beginResetModel()
        if size:
            self.page_size = size
        self.page = max(0, min(page, self.pages - 1))
        self.endResetModel()

    def _visible(self):
        start = self.page * self.page_size
        return self._order[start:start + self.page_size]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._visible())

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.all_rows[self._visible()[index.row()]]
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            return row[index.column()] if index.column() < len(row) else ""
        if role == Qt.TextAlignmentRole and index.column() in self.numeric:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headers[section] if section < len(self.headers) else ""
        return str(self.page * self.page_size + section + 1)

    def sort(self, column, order=Qt.AscendingOrder):
        self.beginResetModel()

        def key(i):
            r = self.all_rows[i]
            v = r[column] if column < len(r) else ""
            return (0, float(v.replace(",", ""))) if column in self.numeric and v.replace(",", "").replace(".", "").isdigit() \
                else (1, v.lower())
        self._order.sort(key=key, reverse=order == Qt.DescendingOrder)
        self.endResetModel()


class GridView(QTableView):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.setObjectName("grid")
        if model is not None:
            self.setModel(model)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setWordWrap(False)

    def save_state(self, state):
        state.v = self.verticalScrollBar().value()
        state.h = self.horizontalScrollBar().value()
        m = self.model()
        if isinstance(m, RowsModel):
            state.page, state.page_size = m.page, m.page_size
        return state

    def restore_state(self, state):
        m = self.model()
        if isinstance(m, RowsModel):
            m.set_page(state.page, state.page_size)
        self.verticalScrollBar().setValue(state.v)
        self.horizontalScrollBar().setValue(state.h)


class Pager(QWidget):
    """Page size select (50, 100, 250) and previous and next."""

    changed = Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        lay = hbox(self, spacing=8)
        self.size = QComboBox()
        for n in PAGE_SIZES:
            self.size.addItem(copy.get("grid.page_size", n=n), n)
        self.size.setMinimumHeight(36)
        self.prev = button(copy.get("grid.prev"), "quiet", "nav")
        self.next = button(copy.get("grid.next"), "quiet", "nav")
        self.where = label("", role="caption")
        for w in (self.size, self.prev, self.where, self.next):
            lay.addWidget(w)
        lay.addStretch(1)
        self.size.currentIndexChanged.connect(lambda _: self._go(0))
        self.prev.clicked.connect(lambda: self._go(self.model.page - 1))
        self.next.clicked.connect(lambda: self._go(self.model.page + 1))
        self._show()

    def _go(self, page):
        self.model.set_page(page, self.size.currentData())
        self._show()
        self.changed.emit()

    def _show(self):
        self.where.setText(copy.get("grid.page_of", page=self.model.page + 1, pages=self.model.pages))


class GridStates:
    """Held by the window: one GridState per (stage ID, grid ID)."""

    def __init__(self):
        self._states = {}

    def get(self, stage_id, grid_id):
        return self._states.setdefault((stage_id, grid_id), GridState())


def grid_with_pager(headers, rows, numeric=()):
    box = QWidget()
    lay = vbox(box, spacing=6)
    model = RowsModel(headers, rows, set(numeric))
    view = GridView(model)
    pager = Pager(model)
    lay.addWidget(view, 1)
    lay.addWidget(pager)
    box.view, box.model, box.pager = view, model, pager
    set_prop(view, "role", "grid")
    return box
