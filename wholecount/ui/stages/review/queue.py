"""Step 2, row by row (SPEC 8.2, board C4): status tabs, filters, selection, bulk actions, the grid and the record panel.
Rows come a page at a time from the session (queue_page). A selection is filters plus exclusions, resolved by the session
when a command runs (H12)."""
import tomllib
from dataclasses import replace
from importlib import resources

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFrame, QLineEdit, QSplitter, QTableView,
                               QWidget)

from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.pages import STATUS_TABS, matching_keys, problem_title, queue_page
from wholecount.ui.stages.review.dialogs import SetAsideDialog
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.pagebar import PageBar
from wholecount.ui.widgets.style import WrapScroll, button, clear, hbox, label, narrow_combo, set_prop, vbox

COLUMNS = ("name", "id", "address", "problem", "counted", "location", "source")
_PROBLEMS = None


def problem_text(rid, key):
    global _PROBLEMS
    if _PROBLEMS is None:
        _PROBLEMS = tomllib.loads(resources.files("wholecount.copy").joinpath("problems.toml").read_text(encoding="utf-8"))
    return _PROBLEMS.get(rid, {}).get(key, "")


class QueueModel(QAbstractTableModel):
    toggled = Signal(str, bool)

    def __init__(self, rows, selected):
        super().__init__()
        self.rows = list(rows)
        self.selected = selected

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS) + 1

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return "" if section == 0 else copy.get(f"review.col.{COLUMNS[section - 1]}")
        return None

    def flags(self, index):
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return f | Qt.ItemIsUserCheckable if index.column() == 0 else f

    def data(self, index, role=Qt.DisplayRole):
        r = self.rows[index.row()]
        if index.column() == 0:
            if role == Qt.CheckStateRole:
                return Qt.Checked if self.selected(r.record_key) else Qt.Unchecked
            if role == Qt.AccessibleTextRole:
                return copy.get("review.queue.tick", name=r.name or r.record_key)
            return None
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        col = COLUMNS[index.column() - 1]
        return {"name": r.name, "id": r.client_id, "address": r.address, "problem": r.problems,
                "counted": copy.get("common.yes" if r.counted else "common.no"), "location": r.location,
                "source": f"{r.source} {r.row_number}"}[col]

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() == 0 and role == Qt.CheckStateRole:
            r = self.rows[index.row()]
            self.toggled.emit(r.record_key, Qt.CheckState(value) == Qt.Checked)
            self.dataChanged.emit(index, index)
            return True
        return False


class QueueGrid(QTableView):
    opened = Signal(int)

    def keyPressEvent(self, ev):
        idx = self.currentIndex()
        if ev.key() == Qt.Key_Space and idx.isValid():
            m = self.model()
            box = m.index(idx.row(), 0)
            now = m.data(box, Qt.CheckStateRole) == Qt.Checked
            m.setData(box, Qt.Unchecked if now else Qt.Checked, Qt.CheckStateRole)
            return
        if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and idx.isValid():
            self.opened.emit(idx.row())
            return
        super().keyPressEvent(ev)


class QueueView(QWidget):
    def __init__(self, window, filt):
        super().__init__()
        self.window_ = window
        self.filt = filt
        self.page = 0
        self.size = 50
        self.picked = set()               # record keys ticked one by one
        self.all_matching = False         # the whole filtered set, less the exclusions
        self.excluded = set()
        self.open_key = None
        self.show_unmatched = False
        lay = vbox(self, spacing=10)
        self.tabs = hbox(spacing=0)
        lay.addLayout(self.tabs)
        self.filters = hbox(spacing=8)
        lay.addLayout(self.filters)
        self.showing = label("", role="caption", name="queueShowing")
        lay.addWidget(self.showing)
        self.select_bar = vbox()
        lay.addLayout(self.select_bar)
        self.bulk = hbox(spacing=8)
        lay.addLayout(self.bulk)
        self.split = QSplitter(Qt.Vertical)
        self.grid = QueueGrid()
        self.grid.setObjectName("queueGrid")
        self.grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grid.verticalHeader().setDefaultSectionSize(36)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self.grid.opened.connect(self._open_row)
        self.grid.doubleClicked.connect(lambda i: self._open_row(i.row()))
        self.split.addWidget(self.grid)
        self.panel_scroll = WrapScroll()
        self.panel_scroll.setObjectName("recordPanel")
        self.split.addWidget(self.panel_scroll)
        self.split.setSizes([450, 550])
        self.panel_scroll.hide()
        self.split.setMinimumHeight(560)
        lay.addWidget(self.split, 1)
        self.pagebar = PageBar(0, 1, self.size)
        self.pagebar.page_changed.connect(self._page)
        self.pagebar.size_changed.connect(self._size)
        lay.addWidget(self.pagebar)
        self.requests = 0
        self.refresh()

    @property
    def session(self):
        return self.window_.bridge.session

    # Data

    def selected(self, rk):
        return (rk not in self.excluded) if self.all_matching else (rk in self.picked)

    def selection_keys(self):
        """The rows a bulk command acts on: resolved from the filters now, never from row positions (H12)."""
        if self.all_matching:
            return [k for k in matching_keys(self.session, self.filt) if k not in self.excluded]
        return sorted(self.picked)

    def _tick(self, rk, on):
        if self.all_matching:
            (self.excluded.discard if on else self.excluded.add)(rk)
        else:
            (self.picked.add if on else self.picked.discard)(rk)
        self._select_bar()
        self._bulk()

    def _page(self, p):
        self.page = p
        self.refresh()

    def _size(self, n):
        self.size, self.page = n, 0
        self.refresh()

    def set_filter(self, **kw):
        self.filt = replace(self.filt, **kw)
        self.page = 0
        self.picked, self.excluded, self.all_matching = set(), set(), False
        self.refresh()

    def refresh(self):
        self.requests += 1
        self.data = queue_page(self.session, self.filt, self.page, self.size)
        v = self.grid.verticalScrollBar().value()
        self.model = QueueModel(self.data.rows, self.selected)
        self.model.toggled.connect(self._tick)
        self.grid.setModel(self.model)
        self.grid.verticalScrollBar().setValue(v)
        self._tabs()
        self._filters()
        self.showing.setText(copy.get("review.queue.showing", m=len(self.data.rows), n=self.data.total))
        self.pagebar.set_pages(self.data.page, self.data.pages)
        self._select_bar()
        self._bulk()
        if self.open_key is not None and self.open_key in self.session.results.outcomes:
            self._panel()

    # Controls

    def _tabs(self):
        clear(self.tabs)
        for st in STATUS_TABS:
            b = button(copy.get(f"review.status.{st}", n=self.data.status_counts.get(st, 0)), "segment", name=f"status_{st}")
            set_prop(b, "selected", st == self.filt.status)
            b.clicked.connect(lambda _=False, st=st: self.set_filter(status=st))
            self.tabs.addWidget(b)
        self.tabs.addStretch(1)

    def _filters(self):
        clear(self.filters)
        prob = QComboBox()
        narrow_combo(prob, 14)
        prob.setObjectName("filterProblem")
        prob.addItem(copy.get("review.filter.any", n=sum(self.data.problem_counts.values())), "")
        for rid, n in sorted(self.data.problem_counts.items(), key=lambda x: -x[1]):
            prob.addItem(copy.get("review.filter.item", name=problem_title(rid), n=n), rid)
        prob.setCurrentIndex(max(0, prob.findData(self.filt.problem)))
        prob.activated.connect(lambda _: self.set_filter(problem=prob.currentData()))
        src = QComboBox()
        narrow_combo(src, 14)
        src.setObjectName("filterSource")
        src.addItem(copy.get("review.filter.any_source"), "")
        for fn in sorted(self.data.source_counts):
            src.addItem(fn, fn)
        src.setCurrentIndex(max(0, src.findData(self.filt.source)))
        src.activated.connect(lambda _: self.set_filter(source=src.currentData()))
        search = QLineEdit(self.filt.search)
        search.setObjectName("queueSearch")
        search.setPlaceholderText(copy.get("review.filter.search"))
        search.returnPressed.connect(lambda: self.set_filter(search=search.text()))
        clear_b = button(copy.get("review.filter.clear"), "quiet", "nav", name="clearFilters")
        clear_b.clicked.connect(lambda: self.set_filter(problem="", source="", search="", cause_id=""))
        for w in (prob, src, search, clear_b):
            self.filters.addWidget(w, 1 if w is search else 0)

    def _select_bar(self):
        clear(self.select_bar)
        page_keys = [r.record_key for r in self.data.rows]
        if not page_keys:
            return
        page_ticked = all(self.selected(k) for k in page_keys)
        box = QCheckBox(copy.get("review.select.page"))
        box.setObjectName("selectPage")
        box.setChecked(page_ticked)
        box.toggled.connect(self._select_page)
        self.select_bar.addWidget(box)
        if page_ticked and self.data.total > len(page_keys) and not self.all_matching:
            f = QFrame()
            f.setObjectName("holdingBar")
            fl = hbox(f, (10, 4, 10, 4), 8)
            b = button(copy.get("review.select.all", m=self.data.total), "quiet", "nav", name="selectAllMatching")
            b.clicked.connect(self._select_all)
            fl.addWidget(b)
            fl.addStretch(1)
            self.select_bar.addWidget(f)

    def _select_page(self, on):
        for r in self.data.rows:
            self._tick(r.record_key, on)
        self.model.layoutChanged.emit()

    def _select_all(self):
        self.all_matching, self.excluded = True, set()
        self.model.layoutChanged.emit()
        self._select_bar()
        self._bulk()

    def _bulk(self):
        clear(self.bulk)
        n = len(self.selection_keys()) if (self.picked or self.all_matching) else 0
        self.bulk.addWidget(label(copy.get("review.select.count", n=n), role="note", name="selectedCount"))
        clr = button(copy.get("review.select.clear"), "quiet", "nav", name="clearSelection")
        clr.clicked.connect(self._clear_selection)
        self.bulk.addWidget(clr)
        for key, fn in (("approve", self.approve), ("aside", self.aside), ("reopen", self.reopen),
                        ("keep_one", self.keep_one)):
            b = button(copy.get(f"review.bulk.{key}"), "secondary", name=f"bulk_{key}")
            b.clicked.connect(fn)
            self.window_.run_hold.register(b)
            b.setVisible(n > 0)
            self.bulk.addWidget(b)
        self.bulk.addStretch(1)

    def _clear_selection(self):
        self.picked, self.excluded, self.all_matching = set(), set(), False
        self.refresh()

    # Bulk commands, each one Undo step

    def approve(self):
        from wholecount.session.reviewer_view import needs_second

        keys = self.selection_keys()
        second = None
        if needs_second(len(keys)):
            second = self.window_.ask_text(copy.get("review.second.title"), copy.get("review.second.prompt", n=len(keys)))
            if not second:
                return
        self.window_.bridge.dispatch(C.ApproveRows(keys, "*", second))
        self._clear_selection()

    def aside(self):
        d = SetAsideDialog(self.window_, self.selection_keys())
        d.accepted.connect(self._clear_selection)
        self.window_.active_dialog = d
        d.open()
        return d

    def reopen(self):
        self.window_.bridge.dispatch(C.ReturnToOpen(self.selection_keys()))
        self._clear_selection()

    def keep_one(self):
        from wholecount.session.pages import keep_one_plan

        keys = self.selection_keys()
        kept, aside = keep_one_plan(self.session, keys)
        if not self.window_.confirm(copy.get("review.keep_one.title"), (copy.get("review.keep_one.plan", k=kept, j=aside),),
                                    copy.get("review.keep_one.ok"), copy.get("close.keep")):
            return
        self.window_.bridge.dispatch(C.KeepOnePerProgram(keys))
        self._clear_selection()

    # The record panel

    def _open_row(self, row):
        if 0 <= row < len(self.data.rows):
            self.open_key = self.data.rows[row].record_key
            self._panel()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape and self.panel_scroll.isVisible():
            self.open_key = None
            self.panel_scroll.hide()
            return
        super().keyPressEvent(ev)

    def _panel(self):
        from wholecount.ui.stages.review.record import RecordPanel

        self.record = RecordPanel(self.window_, self.open_key, self.show_unmatched, self._toggle_unmatched, self._open_key)
        self.panel_scroll.setWidget(self.record)
        self.panel_scroll.show()

    def _toggle_unmatched(self):
        self.show_unmatched = not self.show_unmatched
        self._panel()

    def _open_key(self, rk):
        self.open_key = rk
        self._panel()
