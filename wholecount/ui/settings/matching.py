"""Measure matching (SPEC 8.8, M13 CAL-1 to CAL-5): the Settings card and the 1,100 by 720 window with five steps, Draw,
Label, Settle, Known pairs and Results."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QSpinBox, QStackedWidget, QTableWidget, QWidget

from wholecount import copy
from wholecount.session import calibration as cs
from wholecount.ui.settings.label import LabelView
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.style import button, clear, hbox, label, set_prop, vbox

STEPS = ("draw", "label", "settle", "known", "results")


def _band_text(key, b, **kw):
    """A band's sentence: scores lo to hi, or lo and up for the top band."""
    edges = cs.band_edges()
    if b < len(edges):
        return copy.get(key, lo=edges[b - 1], hi=edges[b] - 1, **kw)
    if key.endswith("unmeasured"):
        return copy.get(key, lo=edges[b - 1], hi=200, **kw)
    return copy.get(key + "_top", lo=edges[b - 1], **kw)


class MatchingWindow(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.cal = None
        self.setModal(True)
        self.setObjectName("matchingWindow")
        self.resize(1100, 720)
        self.setWindowTitle(copy.get("matching.title"))
        lay = vbox(self, (24, 20, 24, 20), 12)
        lay.addWidget(label(copy.get("matching.title"), role="h2"))
        tabs = hbox(spacing=0)
        self.step_buttons = {}
        for i, sid in enumerate(STEPS):
            b = button(copy.get(f"matching.step.{sid}"), "segment", name=f"matchStep_{sid}")
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            self.step_buttons[sid] = b
            tabs.addWidget(b)
        tabs.addStretch(1)
        lay.addLayout(tabs)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.pages = {sid: QWidget() for sid in STEPS}
        for sid in STEPS:
            vbox(self.pages[sid], spacing=10)
            self.stack.addWidget(self.pages[sid])
        self.message = label("", role="note", tone="amber", wrap=True, name="matchMessage")
        lay.addWidget(self.message)
        self._draw_page()
        self.go(0)

    def go(self, i):
        self.stack.setCurrentIndex(i)
        for k, sid in enumerate(STEPS):
            set_prop(self.step_buttons[sid], "selected", k == i)
            self.step_buttons[sid].setEnabled(k == 0 or self.cal is not None)
        sid = STEPS[i]
        if sid == "settle":
            self._settle_page()
        elif sid == "known":
            self._known_page()
        elif sid == "results":
            self._results_page()

    # Draw

    def _draw_page(self):
        lay = self.pages["draw"].layout()
        clear(lay)
        row = hbox(spacing=8)
        row.addWidget(label(copy.get("matching.draw.per_band"), role="note"))
        self.per_band = QSpinBox()
        self.per_band.setObjectName("perBand")
        cal = cs.settings()
        self.per_band.setRange(cal["per_band_min"], cal["per_band_max"])
        self.per_band.setValue(cal["per_band"])
        row.addWidget(self.per_band)
        self.draw_button = button(copy.get("matching.draw.button"), "primary", name="drawPairs")
        self.draw_button.clicked.connect(lambda: self.draw())
        row.addWidget(self.draw_button)
        row.addStretch(1)
        lay.addLayout(row)
        self.draw_counts = vbox(spacing=4)
        lay.addLayout(self.draw_counts)
        lay.addStretch(1)

    def draw(self):
        from wholecount.ui.jobs.actions import CalibrateJob

        d = self.window_.bridge.dpapi or (None, None)
        return self.window_.start_job(CalibrateJob(self.window_.bridge.session, self.per_band.value(), self._drawn, *d))

    def _drawn(self, cal):
        self.cal = cal
        try:
            cal.restore_draft()
        except cs.CalibrationRefused as e:
            self.message.setText(copy.get(f"calibration.refused.{e.code}"))
        clear(self.draw_counts)
        for b in sorted({p.band for p in cal.pairs if p.band}):
            n = sum(1 for p in cal.pairs if p.band == b)
            self.draw_counts.addWidget(label(_band_text("matching.draw.band", b, n=n), role="note", name=f"drawn_{b}"))
        self.draw_counts.addWidget(label(copy.get("matching.draw.joins", n=sum(1 for p in cal.pairs if p.kind == "join")),
                                         role="note"))
        lay = self.pages["label"].layout()
        clear(lay)
        self.labeler = LabelView(self.window_, cal)
        self.labeler.done.connect(lambda: self.go(2))
        lay.addWidget(self.labeler)
        self.go(1)

    # Settle

    def _settle_page(self):
        lay = self.pages["settle"].layout()
        clear(lay)
        if self.cal is None or not self.cal.both_finished():
            lay.addWidget(label(copy.get("calibration.refused.labels_hidden"), role="note"))
            return
        a, b = self.cal.labelers
        left = self.cal.disagreements()
        if not left:
            lay.addWidget(label(copy.get("matching.settle.none"), role="note", name="settleNone"))
        for pid in left:
            row = hbox(spacing=8)
            row.addWidget(label(copy.get("matching.settle.line", a=a.labeler, b=b.labeler,
                                         la=copy.get(f"matching.label.{a.labels.get(pid, 'unsure')}"),
                                         lb=copy.get(f"matching.label.{b.labels.get(pid, 'unsure')}")), role="note"), 1)
            for value in ("same", "different", "unsure"):
                btn = button(copy.get(f"matching.label.{value}"), "secondary", name=f"settle_{value}_{pid}")
                btn.clicked.connect(lambda _=False, p=pid, v=value: (self.cal.settle(p, v), self._settle_page()))
                row.addWidget(btn)
            lay.addLayout(row)
        lay.addStretch(1)

    # Known pairs

    def _known_page(self):
        lay = self.pages["known"].layout()
        if lay.count():
            return
        lay.addWidget(label(copy.get("matching.known.note", n=cs.settings()["known_pairs_advice"]), role="note", wrap=True,
                            name="knownNote"))
        self.known = QTableWidget(50, 4)
        self.known.setObjectName("knownGrid")
        self.known.setHorizontalHeaderLabels([copy.get(f"matching.known.col.{k}") for k in ("system_a", "id_a", "system_b",
                                                                                              "id_b")])
        lay.addWidget(self.known, 1)
        check = button(copy.get("matching.known.check"), "primary", name="knownCheck")
        check.clicked.connect(lambda: self.check_known())
        lay.addWidget(check, 0, Qt.AlignLeft)
        self.known_result = label("", role="note", name="knownResult")
        lay.addWidget(self.known_result)

    def check_known(self):
        entries = []
        for r in range(self.known.rowCount()):
            cells = [(self.known.item(r, c).text().strip() if self.known.item(r, c) else "") for c in range(4)]
            if all(cells):
                entries.append(cs.KnownPairEntry(*cells))
        res = self.cal.add_known(entries)
        self.known_result.setText(copy.get("matching.known.result", entered=res.entered, compared=len(res.compared),
                                           never=res.never_compared, missing=res.not_in_batch))
        return res

    # Results

    def _results_page(self):
        lay = self.pages["results"].layout()
        clear(lay)
        if self.cal is None or not self.cal.both_finished():
            lay.addWidget(label(copy.get("calibration.refused.labels_hidden"), role="note"))
            return
        rep = self.cal.report()
        for m in rep.measures.bands:
            text = (_band_text("matching.results.band", m.band, same=m.same, labeled=m.labeled, population=m.population)
                    if m.labeled else _band_text("matching.results.unmeasured", m.band, population=m.population))
            lay.addWidget(label(text, role="note", name=f"resultBand_{m.band}"))
        j = rep.joins
        lay.addWidget(label(copy.get(f"calibration.joins.{j.result}", n=j.n, wrong=j.wrong), role="note", wrap=True,
                            name="resultJoins"))
        k = rep.known
        lay.addWidget(label(copy.get("matching.known.result", entered=k.entered, compared=len(k.compared),
                                     never=k.never_compared, missing=k.not_in_batch), role="note", name="resultKnown"))
        lay.addWidget(label(copy.get("matching.results.suggested", n=rep.suggested) if rep.suggested is not None
                            else copy.get("matching.results.no_suggestion"), role="row-title", name="resultSuggested"))
        lay.addWidget(label(copy.get("matching.results.missed", line=rep.line, missed=int(rep.missed)), role="note",
                            name="resultMissed"))
        lay.addWidget(label(copy.get("matching.results.under_floor", floor=cs.settings()["floor"]), role="caption"))
        self.save_button = button(copy.get("matching.results.save"), "primary", name="saveLabels")
        self.save_button.clicked.connect(lambda: self.save())
        lay.addWidget(self.save_button, 0, Qt.AlignLeft)
        self.saved = label("", role="note", name="labelsSaved")
        lay.addWidget(self.saved)
        lay.addStretch(1)
        self.report = rep

    def save(self):
        n = self.cal.save()
        self.window_.bridge.ui["suggested_line"] = self.report.suggested
        self.saved.setText(copy.get("matching.results.saved", n=n))
        self.window_.refresh()
        return n


class MeasureCard(Card):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("measureCard")
        self.body.addWidget(label(copy.get("settings.measure.title"), role="row-title"))
        self.body.addWidget(label(copy.get("settings.measure.body"), role="note", wrap=True, name="measureBody"))
        self.open_button = HeldAction("settings.measure.open", "secondary")
        self.open_button.setObjectName("measureOpen")
        self.open_button.clicked.connect(lambda: self.open_window())
        window.run_hold.register(self.open_button)
        self.body.addWidget(self.open_button, 0, Qt.AlignLeft)
        self.window_dialog = None

    def open_window(self):
        self.window_dialog = MatchingWindow(self.window_)
        self.window_dialog.open()
        return self.window_dialog

    def update_view(self, v):
        s = getattr(self.window_.bridge, "session", None)
        ok = s is not None and cs.can_measure(s)
        self.open_button.set_holds([] if ok else [HoldReason("settings.measure.hold")])
