"""The ledger (SPEC 7.1 to 7.4, 11.3). One LedgerPanel instance: the 280px column when wide, the Details drawer when narrow.

Every number and equation comes from FrameView. The equations are the engine's (A-22); no widget builds one. Before a run
each section says what it doesn't know yet, and while a run goes the result sections say so and never show half a count.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QWidget

from wholecount import copy
from wholecount.ui.theme import color
from wholecount.ui.widgets.confidence import ConfidenceBlock
from wholecount.ui.widgets.style import WrapButton, WrapScroll, button, clear, hbox, label, rule, set_prop, vbox

WIDTH = 280


class StackedBar(QWidget):
    """10px: counted ink, not counted yet blue-500, set aside line-2, inside a 1px line border."""

    def __init__(self, parts, parent=None):
        super().__init__(parent)
        self.parts = parts                # ((count, color name), ...)
        self.setFixedHeight(10)

    def sizeHint(self):
        return QSize(200, 10)

    def paintEvent(self, _):
        p = QPainter(self)
        total = sum(n for n, _ in self.parts) or 1
        x, w = 1, self.width() - 2
        for i, (n, name) in enumerate(self.parts):
            seg = int(round(w * n / total)) if i < len(self.parts) - 1 else (w + 1 - x)
            if seg > 0:
                p.fillRect(x, 1, seg, self.height() - 2, QColor(color(name)))
            x += max(0, seg)
        p.setPen(QPen(QColor(color("line")), 1))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.end()


def _row(name, value, tone=None, outline=False):
    box = hbox(spacing=8)
    n = label(name, role="note", tone=tone or "ink")
    v = label(f"{value:,}", role="row-title", tone=tone or "ink")
    box.addWidget(n, 1)
    box.addWidget(v)
    if outline:
        set_prop(n, "outline", True)
    return box


def count_lines(goal, counts, by_program=False):
    """(big number, sub line key and params) for one goal, from the engine's range and final flag."""
    low, high = goal
    p = "p_" if by_program else ""
    if counts.is_final:
        return f"{low:,}", (f"ledger.counts.{p}final", {})
    if low == high:
        return f"{low:,}", (f"ledger.counts.{p}unique", {})
    if counts.open_pairs and counts.open_copy_groups:
        return f"{low:,}", (f"ledger.counts.{p}range_groups", {"hi": high, "pairs": counts.open_pairs,
                                                                "groups": counts.open_copy_groups})
    if counts.open_copy_groups:
        return f"{low:,}", (f"ledger.counts.{p}range_groups_only", {"hi": high, "groups": counts.open_copy_groups})
    return f"{low:,}", (f"ledger.counts.{p}range", {"hi": high, "pairs": counts.open_pairs})


class Section(QWidget):
    def __init__(self, kicker_key, first=False, blue=False, parent=None):
        super().__init__(parent)
        outer = vbox(self, spacing=10)
        if not first:
            outer.addWidget(rule())
        self.kicker = label(copy.get(kicker_key).upper(), role="ledger-kicker", tone="blue" if blue else None)
        if first:   # M15: the ledger's help sits on its first section
            from wholecount.ui.widgets.help import titled

            outer.addLayout(titled(self.kicker, "el.ledger"))
        else:
            outer.addWidget(self.kicker)
        self.body = vbox(spacing=6)
        outer.addLayout(self.body)

    def reset(self):
        clear(self.body)

    def note(self, key, tone=None, name=None, **params):
        w = label(copy.get(key, **params), role="note", tone=tone, wrap=True, name=name)
        self.body.addWidget(w)
        return w


class LedgerPanel(QFrame):
    open_check = Signal()
    open_your_data = Signal()
    open_settings = Signal()
    change_reviewer = Signal()
    close_app = Signal()
    start_over = Signal()
    acknowledge = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ledger")
        self.setFixedWidth(WIDTH)
        outer = vbox(self)
        self.scroll = WrapScroll()
        inner = QWidget()
        inner.setObjectName("ledgerInner")
        self.lay = vbox(inner, (18, 18, 18, 18), 16)
        self.batch = Section("ledger.kicker.batch", first=True)
        self.standing = Section("ledger.kicker.standing")
        self.stage_slot = vbox()
        self.counts = Section("ledger.kicker.counts", blue=True)
        self.confidence = Section("ledger.kicker.confidence")
        self.conf_block = ConfidenceBlock(_EMPTY, full=True, on_tick=self.acknowledge.emit)
        self.confidence.body.addWidget(self.conf_block)
        self.locations = Section("ledger.kicker.locations")
        for w in (self.batch, self.standing):
            self.lay.addWidget(w)
        self.lay.addLayout(self.stage_slot)
        for w in (self.counts, self.confidence, self.locations):
            self.lay.addWidget(w)
        self.lay.addStretch(1)
        self.scroll.setWidget(inner)
        outer.addWidget(self.scroll, 1)
        self.footer = self._footer()
        outer.addWidget(self.footer)
        self.stage_section = None
        self.compact = False

    def _footer(self):
        f = QFrame()
        f.setObjectName("ledgerFooter")
        lay = vbox(f, (18, 12, 18, 14), 6)
        self.check_line = WrapButton("", name="checkLine")
        self.check_line.clicked.connect(self.open_check)
        self.your_data = button(copy.get("ledger.foot.your_data"), "quiet", "nav", name="yourDataLink")
        self.your_data.clicked.connect(self.open_your_data)
        self.settings = button(copy.get("ledger.foot.settings"), "quiet", "nav", name="settingsLink")
        self.settings.clicked.connect(self.open_settings)
        lay.addWidget(self.check_line)
        for b in (self.your_data, self.settings):
            lay.addWidget(b, 0, Qt.AlignLeft)
        self.trust = label("", role="micro", wrap=True, name="trustSentence")
        lay.addWidget(self.trust)
        rv = hbox(spacing=6)
        self.reviewer = label("", role="note", tone="ink-2", name="reviewerLine")
        self.change = button(copy.get("ledger.foot.change"), "quiet", "nav", name="reviewerChange")
        self.change.clicked.connect(self.change_reviewer)
        rv.addWidget(self.reviewer, 1)
        rv.addWidget(self.change)
        lay.addLayout(rv)
        bottom = hbox(spacing=8)
        self.close_button = button(copy.get("top.close"), "secondary", name="ledgerClose")
        self.close_button.clicked.connect(self.close_app)
        self.start_button = button(copy.get("ledger.foot.start_over"), "quiet", "lesser", name="startOver")
        self.start_button.clicked.connect(self.start_over)
        bottom.addWidget(self.close_button)
        bottom.addWidget(self.start_button)
        bottom.addStretch(1)
        lay.addLayout(bottom)
        return f

    def set_compact(self, compact):
        self.compact = compact
        self.close_button.setVisible(not compact)

    def set_stage_section(self, widget):
        clear(self.stage_slot)
        self.stage_section = widget
        if widget is not None:
            self.stage_slot.addWidget(widget)

    def update_view(self, view):
        self._batch(view)
        self._standing(view)
        self._counts(view)
        self._confidence(view)
        self._locations(view)
        self._foot(view)
        if self.stage_section is not None and hasattr(self.stage_section, "update_view"):
            self.stage_section.update_view(view)
        self.scroll.fit()

    def _waiting(self, view):
        """None when results can show, else the copy key that stands in for them."""
        if view.running:
            return "ledger.standing.running"
        if view.results_stale:
            return "ledger.counts.stale"
        if view.counts is None:
            return ""
        return None

    def _batch(self, v):
        s = self.batch
        s.reset()
        if v.practice:
            s.note("ledger.batch.practice", tone="amber", name="practiceLine")
        if not v.files:
            s.note("ledger.batch.empty")
            return
        if v.rows_in:
            s.note("ledger.batch.rows", rows=v.rows_in, files=v.files)
        s.note("ledger.batch.tables", tables=v.tables)

    def _standing(self, v):
        s = self.standing
        s.reset()
        wait = self._waiting(v)
        if wait == "":
            s.note("ledger.standing.before", name="standingBefore")
            return
        if wait:
            s.note(wait, tone="amber" if wait == "ledger.counts.stale" else None, name="standingWait")
            return
        c = v.counts
        if not c.balance_ok:
            s.note("ledger.standing.unbalanced", tone="amber", name="unbalanced")
        s.body.addWidget(StackedBar(((c.counted, "ink"), (c.not_counted_yet, "blue-500"), (c.set_aside, "line-2"))))
        s.body.addLayout(_row(copy.get("ledger.standing.counted"), c.counted))
        s.body.addLayout(_row(copy.get("ledger.standing.not_counted_yet"), c.not_counted_yet, "blue"))
        s.body.addLayout(_row(copy.get("ledger.standing.set_aside"), c.set_aside))
        if c.lines:
            key, params = c.lines[0]
            s.note(key, tone="muted", name="standingSum", **params)

    def _counts(self, v):
        s = self.counts
        s.reset()
        wait = self._waiting(v)
        if wait == "":
            s.note("ledger.counts.before", name="countsBefore")
            return
        if wait:
            s.note(wait, tone="amber" if wait == "ledger.counts.stale" else None, name="countsWait")
            return
        c = v.counts
        if not c.balance_ok:
            s.note("ledger.standing.unbalanced", tone="amber", name="countsHeld")
            return
        for goal, key, prog in ((c.goal1, "ledger.counts.goal1", False), (c.goal2, "ledger.counts.goal2", True)):
            big, (sub_key, params) = count_lines(goal, c, prog)
            s.body.addWidget(label(copy.get(key), role="caption"))
            s.body.addWidget(label(big, role="count", name="goal2Count" if prog else "goal1Count"))
            s.body.addWidget(label(copy.get(sub_key, **params), role="note", tone="ink-2", wrap=True,
                                   name="goal2Sub" if prog else "goal1Sub"))
        if not c.is_final and c.not_counted_yet:
            s.note("ledger.counts.settled", tone="muted", name="settled", n=c.not_counted_yet)

    def _confidence(self, v):
        wait = self._waiting(v)
        self.conf_block.setVisible(wait is None or wait == "")
        for w in self.confidence.findChildren(QWidget, "confWait"):
            w.setParent(None)
        if wait:
            self.confidence.note(wait, tone="amber" if wait == "ledger.counts.stale" else None, name="confWait")
            return
        self.conf_block.update_view(v if wait is None else _EMPTY, True)

    def _locations(self, v):
        s = self.locations
        s.reset()
        wait = self._waiting(v)
        if wait == "":
            s.note("ledger.loc.before", name="locBefore")
            return
        if wait:
            s.note(wait, tone="amber" if wait == "ledger.counts.stale" else None, name="locWait")
            return
        loc = v.counts.locations
        s.body.addLayout(_row(copy.get("ledger.loc.high"), loc.high))
        s.body.addLayout(_row(copy.get("ledger.loc.low"), loc.low, "amber"))
        s.body.addLayout(_row(copy.get("ledger.loc.not_mapped"), loc.not_mapped, "amber", outline=True))
        for reason in ("no_fixed_address", "outside_nyc", "address_problem", "not_found", "no_geocoder"):
            n = getattr(loc, reason)
            if n > 0:
                box = hbox(margins=(12, 0, 0, 0), spacing=8)
                box.addWidget(label(copy.get(f"status.location.reason.{reason}"), role="caption",
                                    name=f"loc_{reason}"), 1)
                box.addWidget(label(f"{n:,}", role="caption"))
                s.body.addLayout(box)
        if len(v.counts.lines) > 1:
            key, params = v.counts.lines[1]
            s.note(key, tone="muted", name="locSum", **params)
        s.note("ledger.loc.weak", tone="muted")

    def _foot(self, v):
        ok = v.can_place
        self.check_line.setText(copy.get("ledger.foot.check_ok" if ok else "ledger.foot.check_warn"))
        self.check_line.set_tone("nav" if ok else "amber")
        trust = copy.get("ledger.foot.trust_offline") + " " + copy.get("ledger.foot.trust_disk")
        if v.saved_progress:
            trust += " " + copy.get("ledger.foot.trust_saved")
        self.trust.setText(trust)
        if v.reviewer_asked and v.reviewer:
            self.reviewer.setText(copy.get("ledger.foot.reviewer", name=v.reviewer))
        else:
            self.reviewer.setText(copy.get("ledger.foot.reviewer_none"))


class _Empty:
    confidence = None


_EMPTY = _Empty()


class _Counts(QWidget):
    pass


def stage_section_for(stage_id, view):
    from wholecount.ui.frame.sections import SECTIONS

    cls = SECTIONS.get(stage_id)
    return cls(view) if cls else None
