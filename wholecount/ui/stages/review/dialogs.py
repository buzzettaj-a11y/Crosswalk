"""Fix problems dialogs and drawers (M12 section 2): the reviewer prompt, accept all as they are, set all aside, preview,
the fill preview and compare. Each opens without blocking, so a person can read the stage behind it and tests can drive it.

Values show on screen only. No dialog has a free-text box except the reviewer name, the typed count, the second reviewer's
name and the 120-character Other note, and none of those holds a client value (H7).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QLineEdit, QRadioButton,
                               QSpinBox, QWidget)

from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.reviewer_view import ACCEPT_REASONS, SET_ASIDE_REASONS, needs_second, reason_label, sample_rows
from wholecount.ui.frame.drawers import Drawer
from wholecount.ui.widgets.grid import grid_with_pager
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.style import button, clear, hbox, label, narrow_combo, vbox


def _row_values(session, rk):
    row = session.results.rows[rk]
    o = session.results.outcomes[rk]
    from wholecount.session.pages import problem_title

    name = " ".join(v for v in (row.value("First_Name"), row.value("Last_Name")) if v)
    return [name, row.value("Client_ID"), row.value("Address_1"), "; ".join(problem_title(r) for r in o.reasons)]


class ReviewerPrompt(QDialog):
    """Who is reviewing (SPEC 8.7). Shown once a session, the first time Fix problems opens."""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.setModal(True)
        self.setFixedWidth(440)
        lay = vbox(self, (24, 20, 24, 20), 10)
        lay.addWidget(label(copy.get("review.reviewer.title"), role="h3"))
        self.name = QLineEdit(window.bridge.session.reviewer or "")
        self.name.setObjectName("reviewerName")
        lay.addWidget(self.name)
        lay.addWidget(label(copy.get("review.reviewer.line"), role="note", wrap=True))
        self.refusal = label("", role="note", tone="amber", name="reviewerRefusal")
        lay.addWidget(self.refusal)
        row = hbox(spacing=8)
        row.addStretch(1)
        self.not_now = button(copy.get("review.reviewer.not_now"), "secondary", name="reviewerNotNow")
        self.start = button(copy.get("review.reviewer.start"), "primary", name="reviewerStart")
        row.addWidget(self.not_now)
        row.addWidget(self.start)
        lay.addLayout(row)
        self.start.clicked.connect(self.save)
        self.not_now.clicked.connect(self.reject)
        self.start.setDefault(True)

    def save(self):
        msg = self.window_.change_reviewer(self.name.text())
        if msg:
            self.refusal.setText(msg)
            return
        self.accept()


class AcceptDialog(QDialog):
    """Accept all as they are (SPEC 8.7): five sample rows, the typed count, a reason, and a second reviewer over 200."""

    def __init__(self, window, cause_id, record_keys):
        super().__init__(window)
        self.window_ = window
        self.cause_id, self.keys = cause_id, tuple(sorted(record_keys))
        self.setModal(True)
        self.setFixedWidth(560)
        s = window.bridge.session
        lay = vbox(self, (24, 20, 24, 20), 10)
        n = len(self.keys)
        lay.addWidget(label(copy.get("review.accept.title", n=n), role="h3"))
        lay.addWidget(label(copy.get("review.bulk.sample", count=min(5, n)), role="note", wrap=True))
        sample = sample_rows(cause_id, self.keys)
        g = grid_with_pager([copy.get(f"review.col.{k}") for k in ("name", "id", "address", "problem")],
                            [_row_values(s, k) for k in sample])
        g.pager.hide()
        g.setFixedHeight(230)
        self.sample = sample
        lay.addWidget(g)
        lay.addWidget(label(copy.get("review.accept.type", n=n), role="caption"))
        self.typed = QSpinBox()
        self.typed.setObjectName("typedCount")
        self.typed.setRange(0, 10_000_000)
        self.typed.setValue(0)
        lay.addWidget(self.typed)
        lay.addWidget(label(copy.get("review.accept.reason"), role="caption"))
        self.reason = QComboBox()
        narrow_combo(self.reason)
        self.reason.setObjectName("acceptReason")
        self.reason.addItem(copy.get("review.choose"), "")
        for r in ACCEPT_REASONS:
            self.reason.addItem(reason_label("accept", r), r)
        lay.addWidget(self.reason)
        self.second = None
        if needs_second(n):
            lay.addWidget(label(copy.get("review.accept.over"), role="note", tone="amber", wrap=True))
            self.second = QLineEdit()
            self.second.setObjectName("secondReviewer")
            self.second.setPlaceholderText(copy.get("review.accept.second"))
            lay.addWidget(self.second)
            self.second.textChanged.connect(lambda *_: self._holds())
        self.refusal = label("", role="note", tone="amber", name="acceptRefusal", wrap=True)
        lay.addWidget(self.refusal)
        row = hbox(spacing=8)
        row.addStretch(1)
        self.cancel = button(copy.get("review.cancel"), "secondary", name="acceptCancel")
        self.ok = HeldAction("review.accept.ok", "primary", {"n": n})
        self.ok.setObjectName("acceptOk")
        row.addWidget(self.cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.save)
        self.typed.valueChanged.connect(lambda *_: self._holds())
        self.reason.currentIndexChanged.connect(lambda *_: self._holds())
        self.cancel.setFocus(Qt.OtherFocusReason)
        self._holds()

    def _holds(self):
        n = len(self.keys)
        holds = []
        if self.typed.value() != n:
            holds.append(HoldReason("review.accept.hold.count", {"n": n}))
        if not self.reason.currentData():
            holds.append(HoldReason("review.accept.hold.reason"))
        if self.second is not None and not self.second.text().strip():
            holds.append(HoldReason("review.accept.hold.second"))
        self.ok.set_holds(holds)

    def save(self):
        from wholecount.session.reviewer_view import AcceptProof

        proof = AcceptProof(self.typed.value(), self.reason.currentData())
        second = self.second.text().strip() if self.second is not None else None
        result = self.window_.bridge.dispatch(C.AcceptGroup(self.cause_id, self.keys, proof, second))
        if not result.ok:
            self.refusal.setText(copy.get(f"review.refused.{self.window_.bridge.last_refusal}"))
            return
        self.accept()


class SetAsideDialog(QDialog):
    """Set aside with a reason from the fixed list (SPEC 8.1). Other opens a note of up to 120 characters."""

    def __init__(self, window, record_keys):
        super().__init__(window)
        self.window_ = window
        self.keys = tuple(sorted(record_keys))
        self.setModal(True)
        self.setFixedWidth(440)
        lay = vbox(self, (24, 20, 24, 20), 10)
        lay.addWidget(label(copy.get("review.aside.title", n=len(self.keys)), role="h3"))
        self.reason = QComboBox()
        narrow_combo(self.reason)
        self.reason.setObjectName("asideReason")
        self.reason.addItem(copy.get("review.choose"), "")
        for r in SET_ASIDE_REASONS:
            self.reason.addItem(reason_label("set_aside", r), r)
        lay.addWidget(self.reason)
        self.note = QLineEdit()
        self.note.setObjectName("asideNote")
        self.note.setMaxLength(120)
        self.note_warning = label(copy.get("review.aside.note"), role="caption", tone="amber", wrap=True)
        lay.addWidget(self.note)
        lay.addWidget(self.note_warning)
        self.note.hide()
        self.note_warning.hide()
        row = hbox(spacing=8)
        row.addStretch(1)
        self.cancel = button(copy.get("review.cancel"), "secondary", name="asideCancel")
        self.ok = HeldAction("review.aside.ok", "primary", {"n": len(self.keys)})
        self.ok.setObjectName("asideOk")
        row.addWidget(self.cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)
        self.reason.currentIndexChanged.connect(self._changed)
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.save)
        self.cancel.setFocus(Qt.OtherFocusReason)
        self._changed()

    def _changed(self, *_):
        other = self.reason.currentData() == "other"
        self.note.setVisible(other)
        self.note_warning.setVisible(other)
        self.ok.set_holds([] if self.reason.currentData() else [HoldReason("review.accept.hold.reason")])

    def save(self):
        code = self.reason.currentData()
        note = self.note.text().strip() if code == "other" and self.note.text().strip() else None
        if self.window_.bridge.dispatch(C.SetAsideRows(self.keys, code, note)).ok:
            self.accept()


class PreviewDrawer(Drawer):
    """Preview a cause: its first 50 rows and what each action would do, by arithmetic on the balance (no re-run)."""

    def __init__(self, parent, window):
        super().__init__(parent, "right", 720, "review.preview.kicker", None)
        self.window_ = window
        self.content = vbox()
        self.body.addLayout(self.content)

    def show_cause(self, cause):
        clear(self.content)
        s = self.window_.bridge.session
        c = s.results.counts
        keys = cause.record_keys
        not_counted = sum(1 for k in keys if s.results.outcomes[k].count_status.value == "not_counted_yet")
        self.content.addWidget(label(copy.get(cause.title_key) if not cause.title_key.startswith("problems.")
                                     else _problem_title(cause.cause_id), role="drawer-title", wrap=True))
        if "approve" in cause.actions or "accept_group" in cause.actions:
            self.content.addWidget(label(copy.get("review.preview.accept", a=c.counted, b=c.counted + not_counted),
                                         role="note", wrap=True, name="previewAccept"))
        if "set_aside" in cause.actions:
            self.content.addWidget(label(copy.get("review.preview.aside", a=c.set_aside, b=c.set_aside + len(keys)),
                                         role="note", wrap=True))
        self.content.addWidget(label(copy.get("review.preview.note"), role="note", tone="muted", name="previewNote"))
        g = grid_with_pager([copy.get(f"review.col.{k}") for k in ("name", "id", "address", "problem")],
                            [_row_values(s, k) for k in keys[:50]])
        g.setMinimumHeight(360)
        self.content.addWidget(g)
        self.scroll.fit()


def _problem_title(rid):
    from wholecount.session.pages import problem_title

    return problem_title(rid)


class FillPreview(Drawer):
    """Look up {n} addresses: what would be filled, and what is left alone. Nothing changes until Apply (P-GEO-9)."""

    applied = Signal(int, int)

    def __init__(self, parent, window):
        super().__init__(parent, "right", 720, None, None)
        self.window_ = window
        self.content = vbox()
        self.body.addLayout(self.content)
        self.boxes = {}

    def show_fills(self, cause_id, record_keys):
        clear(self.content)
        s = self.window_.bridge.session
        fills = {k: s.results.fills[k] for k in record_keys if k in s.results.fills}
        left = [k for k in record_keys if k not in fills]
        self.cause_id = cause_id
        self.content.addWidget(label(copy.get("review.fill.heading", n=len(record_keys)), role="drawer-title"))
        self.content.addWidget(label(copy.get("review.fill.title"), role="note", name="fillTitle"))
        self.content.addWidget(label(copy.get("review.fill.counts", a=len(fills), b=len(left)), role="caption"))
        grid = QGridLayout()
        for i, k in enumerate(("name", "row", "source", "was", "becomes", "why")):
            grid.addWidget(label(copy.get(f"review.fill.col.{k}"), role="column-head"), 0, i + 1)
        self.boxes = {}
        r = 1
        for rk, props in sorted(fills.items()):
            row = s.results.rows[rk]
            box = QCheckBox()
            box.setChecked(True)
            box.setObjectName(f"fill_{rk}")
            self.window_.run_hold.register(box)
            self.boxes[rk] = box
            grid.addWidget(box, r, 0)
            name = " ".join(v for v in (row.value("First_Name"), row.value("Last_Name")) if v)
            p = props[0]
            for i, text in enumerate((name, str(row.row_number), s.results.file_of_record[rk], row.value(p.field),
                                      p.value, copy.get("review.fill.why", field=p.field))):
                grid.addWidget(label(text, role="note", wrap=i == 5), r, i + 1)
            r += 1
        self.content.addLayout(grid)
        if left:
            self.content.addWidget(label(copy.get("review.fill.left", n=len(left)), role="caption", wrap=True))
        row = hbox(spacing=8)
        self.apply = button(copy.get("review.fill.apply", k=len(fills)), "primary", name="fillApply")
        self.cancel_ = button(copy.get("review.cancel"), "secondary", name="fillCancel")
        self.window_.run_hold.register(self.apply)
        self.apply.clicked.connect(self.do_apply)
        self.cancel_.clicked.connect(self.close_)
        row.addWidget(self.apply)
        row.addWidget(self.cancel_)
        row.addStretch(1)
        self.content.addLayout(row)
        self.scroll.fit()

    def do_apply(self):
        keys = [k for k, b in self.boxes.items() if b.isChecked()]
        if not keys:
            return
        s = self.window_.bridge.session
        self.window_.bridge.dispatch(C.AcceptFills(keys))
        still = sum(1 for k in keys if s.results.outcomes[k].reasons)
        self.window_.toast = copy.get("review.fill.toast", k=len(keys) - still, j=still)
        self.applied.emit(len(keys) - still, still)
        self.close_()


class ComparePanel(QFrame):
    """Compare the {g}: one group at a time, a row per record, differing fields in 800 weight (SPEC 8.1, H5)."""

    def __init__(self, window, groups, kind):
        super().__init__()
        self.window_ = window
        self.groups = list(groups)
        self.kind = kind
        self.i = 0
        self.setObjectName("card")
        self.lay = vbox(self, (18, 14, 18, 14), 10)
        self.draw()

    def draw(self):
        clear(self.lay)
        s = self.window_.bridge.session
        g = self.groups[self.i]
        top = hbox(spacing=8)
        top.addWidget(label(copy.get("review.compare.group", i=self.i + 1, g=len(self.groups)), role="row-title"), 1)
        prev = button(copy.get("grid.prev"), "quiet", "nav", name="comparePrev")
        nxt = button(copy.get("grid.next"), "quiet", "nav", name="compareNext")
        prev.clicked.connect(lambda: self.go(-1))
        nxt.clicked.connect(lambda: self.go(1))
        prev.setVisible(self.i > 0)
        nxt.setVisible(self.i < len(self.groups) - 1)
        top.addWidget(prev)
        top.addWidget(nxt)
        self.lay.addLayout(top)
        if self.kind == "same_id":
            self.lay.addWidget(label(copy.get("review.compare.same_id"), role="note", wrap=True))
        members = sorted(g.members, key=lambda k: (s.results.file_of_record.get(k, ""), s.results.outcomes[k].row_number))
        fields = [f.key for f in s.schema().enabled_fields()]
        rows = [s.results.rows[k] for k in members]
        differ = [f for f in fields if len({r.value(f) for r in rows}) > 1]
        grid = QGridLayout()
        grid.addWidget(label(copy.get("review.compare.row"), role="column-head"), 0, 1)
        grid.addWidget(label(copy.get("review.fill.col.source"), role="column-head"), 0, 2)
        for i, f in enumerate(differ):
            grid.addWidget(label(f, role="column-head"), 0, 3 + i)
        self.keep = QButtonGroup(self)
        self.radios = {}
        for r, (k, row) in enumerate(zip(members, rows), start=1):
            rb = QRadioButton()
            rb.setObjectName(f"keep_{k}")
            rb.setChecked(r == 1)
            self.keep.addButton(rb)
            self.radios[k] = rb
            self.window_.run_hold.register(rb)
            grid.addWidget(rb, r, 0)
            grid.addWidget(label(str(row.row_number), role="note"), r, 1)
            grid.addWidget(label(s.results.file_of_record.get(k, ""), role="note"), r, 2)
            for i, f in enumerate(differ):
                grid.addWidget(label(row.value(f), role="row-title", tone="blue", name=f"diff_{f}_{r}"), r, 3 + i)
        self.differ = differ
        self.lay.addLayout(grid)
        row = hbox(spacing=8)
        same = button(copy.get("review.compare.same"), "primary", name="compareSame")
        diff = button(copy.get("review.compare.different"), "secondary", name="compareDifferent")
        same.clicked.connect(lambda: self.decide(True))
        diff.clicked.connect(lambda: self.decide(False))
        for b in (same, diff):
            self.window_.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        self.lay.addLayout(row)

    def go(self, d):
        self.i = max(0, min(len(self.groups) - 1, self.i + d))
        self.draw()

    def decide(self, same):
        g = self.groups[self.i]
        if self.kind == "same_id":
            cmd = C.DecideSameIdConflict(g.group_id, "approved_as_entered" if same else "different_people")
        elif same:
            kept = next(k for k, rb in self.radios.items() if rb.isChecked())
            cmd = C.KeepOneInCopyGroup(g.group_id, kept)
        else:
            cmd = C.MarkNotCopies(g.group_id)
        self.window_.bridge.dispatch(cmd)


REFUSAL_KEY = {"signature_missing": "review.corrections.refused.signature",
               "signature_wrong": "review.corrections.refused.signature",
               "originals_changed": "review.corrections.refused.changed",
               "unknown_record": "review.corrections.refused.unknown",
               "other_column_changed": "review.corrections.refused.other_column",
               "field_not_failing": "review.corrections.refused.other_column"}


def refusal_sentence(refusal):
    """One fixed reason per refused row. Column names are field or header names, never values (H8)."""
    key = REFUSAL_KEY.get(refusal.code)
    if key is None:
        return copy.get(refusal.sentence_key)
    if key.endswith("other_column"):
        return copy.get(key, column=refusal.column or "")
    return copy.get(key)


class CorrectionsDrawer(Drawer):
    """What a corrections file did (SPEC 8.6): accepted, refused and now counted, then each refused row with its file row
    number and one reason. Rows matched by Record_Key, so the order of the file never matters."""

    def __init__(self, parent, window):
        super().__init__(parent, "right", 620, None, None)
        self.window_ = window
        self.content = vbox()
        self.body.addLayout(self.content)

    def show_result(self, got, now_count):
        clear(self.content)
        self.content.addWidget(label(got.file_name, role="kicker"))
        self.content.addWidget(label(copy.get("review.corrections.result", a=len(got.accepted), b=len(got.refused),
                                              c=now_count), role="drawer-title", wrap=True, name="correctionsResult"))
        for i, r in enumerate(sorted(got.refused, key=lambda x: (x.line is None, x.line or 0))):
            why = refusal_sentence(r)
            text = copy.get("review.corrections.line", line=r.line, why=why) if r.line is not None else why
            self.content.addWidget(label(text, role="note", tone="amber", wrap=True, name=f"refused_{i}"))
        self.scroll.fit()
