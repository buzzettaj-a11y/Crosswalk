"""The Fix problems body: the head, the reviewer prompt, the two-step header, no longer apply, the causes and the queue."""
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFrame, QWidget

from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.pages import QueueFilter, cause_views, gate, other_files_people, problem_title
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages.review.dialogs import (AcceptDialog, ComparePanel, CorrectionsDrawer, FillPreview, PreviewDrawer,
                                                 ReviewerPrompt, SetAsideDialog)
from wholecount.ui.stages.review.queue import QueueView
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.grid import grid_with_pager
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.style import button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tonetag import ToneTag

TABS = ("counts", "location", "look")
TAG = {"open": ("review.tag.needs", "needs_you"), "decided": ("review.tag.decided", "decided"),
       "settled": ("review.tag.settled", "settled")}


def cause_title(cause):
    if cause.title_key.startswith("problems."):
        return problem_title(cause.cause_id)
    return copy.get(cause.title_key)


class ReviewBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=14)
        self.corrections = HeldAction("review.corrections.button", "secondary")
        self.corrections.setObjectName("applyCorrections")
        self.corrections.clicked.connect(self.apply_corrections)
        window.run_hold.register(self.corrections)
        self.finish = HeldAction("review.finish", "primary")
        self.finish.setObjectName("finishReview")
        self.finish.clicked.connect(self.finish_review)
        window.run_hold.register(self.finish)
        self.head = StageHead("review", [self.corrections, self.finish], saved_progress=v.saved_progress,
                              data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.empty = vbox()
        lay.addLayout(self.empty)
        self.steps = QFrame()
        self.steps.setObjectName("twoStep")
        sl = hbox(self.steps, spacing=0)
        self.step1 = button("", "segment", name="step1")
        self.step2 = button("", "segment", name="step2")
        for i, b in enumerate((self.step1, self.step2), start=1):
            b.setMinimumHeight(64)
            b.clicked.connect(lambda _=False, i=i: self.set_step(i))
            sl.addWidget(b, 1)
        lay.addWidget(self.steps)
        self.nolonger = vbox(spacing=6)
        lay.addLayout(self.nolonger)
        self.area = vbox(spacing=10)
        lay.addLayout(self.area)
        lay.addStretch(1)
        self.step = None
        self.tab = None
        self.queue = None
        self.compare = None
        self.show_nolonger = False
        self.preview = PreviewDrawer(window.centralWidget(), window)
        self.fill = FillPreview(window.centralWidget(), window)
        self.corrections_result = CorrectionsDrawer(window.centralWidget(), window)
        self.dialog = None
        self.update_view(v)
        if window.queue_request:
            status, window.queue_request = window.queue_request, None
            self.set_step(2, QueueFilter(status=status))

    @property
    def session(self):
        return self.window_.bridge.session

    def showEvent(self, ev):
        super().showEvent(ev)
        self.ask_reviewer()

    def ask_reviewer(self):
        """Once a session, the first time this stage opens. It waits while a run goes."""
        b = self.window_.bridge
        if self.session is None or self.session.results is None or b.ui.get("reviewer_asked") or self.window_.run_hold.active:
            return
        b.ui["reviewer_asked"] = True
        self.dialog = ReviewerPrompt(self.window_)
        self.dialog.rejected.connect(self._not_now)
        self.dialog.open()

    def _not_now(self):
        self.window_.bridge.ui["reviewer_asked"] = False
        self.window_.go_to(self.window_.previous_stage or "summary")

    # Head

    def apply_corrections(self):
        path, _ = QFileDialog.getOpenFileName(self, copy.get("review.corrections.button"), "",
                                              copy.get("review.corrections.filter"))
        if path:
            self.start_corrections(pathlib.Path(path))

    def start_corrections(self, path):
        from wholecount.ui.jobs.actions import CorrectionsJob

        def done(got, now_count):
            self.corrections_result.show_result(got, now_count)
            self.corrections_result.open_()
        return self.window_.start_job(CorrectionsJob(self.session, path, done))

    def finish_review(self):
        g = gate(self.session)
        if g.held:
            return
        open_rows = sum(1 for o in self.session.results.outcomes.values() if o.reasons and o.set_aside_reason is None
                        and not o.counted)
        if open_rows and not self.window_.confirm(copy.get("review.finish_title"),
                                                  (copy.get("review.finish_confirm", count=open_rows),),
                                                  copy.get("review.finish_anyway"), copy.get("review.keep_reviewing")):
            return
        self.window_.bridge.dispatch(C.FinishReview(open_rows))
        self.window_.go_to("summary")

    # Steps

    def set_step(self, i, filt=None):
        self.step = i
        if i == 2 and filt is not None:
            self.queue_filter = filt
        self._draw_area()

    def _step_buttons(self, views):
        counts = [v for v in views if v.cause.tab == "counts"]
        open_ = [v for v in counts if v.state == "open"]
        rows = len({k for v in open_ for k in v.cause.record_keys})
        line1 = (copy.get("review.step1.left", n=len(open_), m=len(counts), rows=rows) if open_
                 else copy.get("review.step1.done", m=len(counts)))
        waiting = sum(1 for o in self.session.results.outcomes.values() if o.reasons and o.set_aside_reason is None)
        for b, kicker, title, line, i in ((self.step1, "review.step1.kicker", "review.step1.title", line1, 1),
                                          (self.step2, "review.step2.kicker", "review.step2.title",
                                           copy.get("review.step2.line", n=waiting), 2)):
            b.setText(f"{copy.get(kicker)}   {copy.get(title)}   {line}")
            b.setAccessibleName(f"{copy.get(kicker)}, {copy.get(title)}, {line}")
            set_prop(b, "selected", self.step == i)

    def _nolonger(self):
        clear(self.nolonger)
        nla = self.session.results.no_longer_apply
        if not nla:
            return
        c = Callout("wrong")
        c.setObjectName("noLonger")
        c.body.addWidget(label(copy.get("review.nolonger.title", n=len(nla)), role="row-title", tone="amber"))
        c.body.addWidget(label(copy.get("review.nolonger.line"), role="note", wrap=True))
        show = button(copy.get("src.show_them"), "quiet", "nav", name="showNoLonger")
        show.clicked.connect(self._toggle_nolonger)
        c.body.addWidget(show, 0, Qt.AlignLeft)
        if self.show_nolonger:
            for i, n in enumerate(nla):
                row = hbox(spacing=8)
                rks = n.decision.record_keys
                where = ""
                if rks and rks[0] in self.session.results.outcomes:
                    o = self.session.results.outcomes[rks[0]]
                    where = copy.get("review.nolonger.where", file=self.session.results.file_of_record.get(rks[0], ""),
                                     n=o.row_number)
                row.addWidget(label(copy.get("review.nolonger.row", kind=copy.get(f"review.kind.{n.decision.kind}"),
                                             where=where, why=copy.get(f"review.nolonger.why.{n.reason}")),
                                    role="note", wrap=True), 1)
                again = button(copy.get("review.nolonger.again"), "quiet", "nav", name=f"again_{i}")
                again.clicked.connect(lambda _=False, rks=rks: rks and self.window_.bridge.dispatch(C.ReturnToOpen(
                    [k for k in rks if k in self.session.results.outcomes])))
                self.window_.run_hold.register(again)
                row.addWidget(again)
                c.body.addLayout(row)
        self.nolonger.addWidget(c)

    def _toggle_nolonger(self):
        self.show_nolonger = not self.show_nolonger
        self._nolonger()

    # Step 1

    def _tabs(self, views):
        row = hbox(spacing=0)
        for t in TABS:
            n = len({k for v in views if v.cause.tab == t for k in v.cause.record_keys})
            b = button(copy.get(f"review.tab.{t}", n=n), "segment", name=f"tab_{t}")
            set_prop(b, "selected", t == self.tab)
            b.clicked.connect(lambda _=False, t=t: self._set_tab(t))
            row.addWidget(b)
        row.addStretch(1)
        return row

    def _set_tab(self, t):
        self.tab = t
        self._draw_area()

    def _causes(self, views):
        intro = {"counts": "review.counts.intro", "location": "review.loc.intro", "look": "review.look.intro"}[self.tab]
        self.area.addWidget(label(copy.get(intro), role="note", wrap=True, name=f"intro_{self.tab}"))
        shown = [v for v in views if v.cause.tab == self.tab or (self.tab == "counts" and v.cause.tab == "settled")]
        for v in shown:
            self.area.addWidget(self._card(v))
        if self.tab == "counts":
            n = other_files_people(self.session)
            if n:
                f = QFrame()
                f.setObjectName("card")
                fl = hbox(f, (14, 10, 14, 10), 8)
                fl.addWidget(label(copy.get("review.cross_file_note", count=n), role="note", wrap=True), 1)
                fl.addWidget(ToneTag(copy.get("review.tag.no_decision"), "neutral"))
                self.area.addWidget(f)

    def _card(self, v):
        c = v.cause
        f = QFrame()
        set_prop(f, "callout", {"open": "needs", "decided": "decided", "settled": "ink"}[v.state])
        f.setObjectName(f"cause_{c.cause_id}")
        lay = hbox(f, (16, 12, 16, 12), 14)
        lay.addWidget(label(f"{c.count:,}", role="count-row"), 0, Qt.AlignTop)
        mid = vbox(spacing=6)
        top = hbox(spacing=8)
        top.addWidget(label(cause_title(c), role="row-title", wrap=True), 1)
        text, tone = TAG[v.state]
        top.addWidget(ToneTag(copy.get(text), tone))
        mid.addLayout(top)
        if c.routed:
            mid.addWidget(label(copy.get("review.sent_to_row"), role="caption"))
        diag = self.window_.bridge.diagnosis(c) if c.kind == "other" and c.tab == "location" else None
        if diag is not None:
            d = Callout("needs")
            d.body.addWidget(label(copy.get("review.diag.bold"), role="row-title"))
            d.body.addWidget(label(copy.get("review.mapping_diagnosis", field=diag.field, column_now=diag.column_now,
                                            column_better=diag.column_better, count=diag.rows_fixed), role="note", wrap=True))
            fix = button(copy.get("review.diag.fix"), "primary", name=f"diagFix_{c.cause_id}")
            fix.clicked.connect(lambda _=False, d=diag: self.window_.fix_mapping_and_run(d))
            self.window_.run_hold.register(fix)
            d.body.addWidget(fix, 0, Qt.AlignLeft)
            mid.addWidget(d)
        row = hbox(spacing=6)
        for key, fn in self._actions(c, v):
            b = button(key[0], key[1], key[2] if len(key) > 2 else None, name=f"{key[3]}_{c.cause_id}")
            b.clicked.connect(fn)
            if key[3] not in ("preview", "look"):
                self.window_.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        mid.addLayout(row)
        lay.addLayout(mid, 1)
        return f

    def _actions(self, c, v):
        """(button text, kind, tone, name) and the handler, by cause kind (SPEC 8.1)."""
        out = []
        n = len(c.record_keys)
        if c.kind == "settled":
            return [((copy.get("review.act.look"), "quiet", "nav", "look"),
                     lambda: self.set_step(2, QueueFilter(status="set_aside")))]
        if c.kind in ("copies", "same_id"):
            groups = self._groups_for(c)
            out.append(((copy.get("review.act.compare", g=len(groups)), "primary", None, "compare"),
                        lambda _=False, c=c: self.open_compare(c)))
            if c.kind == "same_id":
                out.append(((copy.get("review.act.route"), "secondary", None, "route"),
                            lambda _=False, c=c: self.route(c)))
            out.append(((copy.get("review.act.preview"), "quiet", "nav", "preview"), lambda _=False, c=c: self.open_preview(c)))
            return out
        if v.state == "settled":
            return out
        if c.kind == "fill_from_street":
            out.append(((copy.get("review.act.lookup", n=n), "primary", None, "lookup"), lambda _=False, c=c: self.look_up(c)))
        if c.kind == "no_address" or "set_aside" in c.actions:
            out.append(((copy.get("review.act.aside"), "secondary", None, "aside"), lambda _=False, c=c: self.set_aside(c)))
        out.append(((copy.get("review.act.route"), "secondary", None, "route"), lambda _=False, c=c: self.route(c)))
        if "accept_group" in c.actions or "approve" in c.actions:
            out.append(((copy.get("review.act.accept"), "secondary", None, "accept"), lambda _=False, c=c: self.accept_all(c)))
        out.append(((copy.get("review.act.preview"), "quiet", "nav", "preview"), lambda _=False, c=c: self.open_preview(c)))
        return out

    def _groups_for(self, c):
        keys = set(c.record_keys)
        return [g for g in self.session.results.open_groups if set(g.members) & keys] or \
               [g for g in self.session.results.groups if g.kind == "same_id_different" and set(g.members) & keys]

    # Cause actions

    def accept_all(self, c):
        self.dialog = AcceptDialog(self.window_, c.cause_id, c.record_keys)
        self.dialog.open()
        return self.dialog

    def set_aside(self, c, keys=None):
        self.dialog = SetAsideDialog(self.window_, keys or c.record_keys)
        self.dialog.open()
        return self.dialog

    def route(self, c):
        self.window_.bridge.dispatch(C.SendToRowByRow(c.cause_id))
        self.set_step(2, QueueFilter(cause_id=c.cause_id))

    def open_preview(self, c):
        self.preview.show_cause(c)
        self.preview.open_()

    def look_up(self, c):
        from wholecount.ui.jobs.actions import LookUpJob

        def done(cause_id, keys):
            self.fill.show_fills(cause_id, keys)
            self.fill.open_()
        return self.window_.start_job(LookUpJob(self.session, c.cause_id, c.record_keys, done))

    def open_compare(self, c):
        groups = self._groups_for(c)
        if not groups:
            return None
        self.compare = ComparePanel(self.window_, groups, c.kind)
        self._draw_area()
        return self.compare

    # Drawing

    def _draw_area(self):
        clear(self.area)
        s = self.session
        if s is None or s.results is None:
            return
        views = cause_views(s)
        self._step_buttons(views)
        if self.compare is not None:
            back = button(copy.get("review.compare.back"), "quiet", "nav", name="compareBack")
            back.clicked.connect(self._close_compare)
            self.area.addWidget(back, 0, Qt.AlignLeft)
            self.area.addWidget(self.compare)
            return
        if self.step == 1:
            self.area.addLayout(self._tabs(views))
            self._causes(views)
        else:
            self.queue = QueueView(self.window_, getattr(self, "queue_filter", QueueFilter()))
            self.area.addWidget(self.queue)

    def _close_compare(self):
        self.compare = None
        self._draw_area()

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        clear(self.empty)
        s = self.session
        if s is None or s.results is None or v.results_stale:
            self.steps.hide()
            c = Callout("wrong")
            c.body.addWidget(label(copy.get("review.not_run" if s is None or s.results is None else "results.held"),
                                   role="note", wrap=True))
            go = button(copy.get("results.go_process"), "primary", name="goProcess")
            go.clicked.connect(lambda: self.window_.go_to("run"))
            c.body.addWidget(go, 0, Qt.AlignLeft)
            self.empty.addWidget(c)
            clear(self.area)
            self.finish.set_holds([HoldReason("results.hold_stale")])
            return
        self.steps.show()
        views = cause_views(s)
        if self.step is None:
            self.step = 1 if any(x.state == "open" and x.cause.tab == "counts" for x in views) else 2
        if self.tab is None:
            self.tab = next((t for t in TABS if any(x.state == "open" and x.cause.tab == t for x in views)), "counts")
        g = gate(s)
        self.finish.set_holds([HoldReason("review.hold.causes", {"n": len(g.left)})] if g.held else [])
        if self.compare is not None:
            self.compare.groups = [x for x in self.compare.groups if x in s.results.open_groups] or self.compare.groups
            if self.compare.i >= len(self.compare.groups):
                self.compare.i = 0
            self.compare.draw()
        self._nolonger()
        self._draw_area()


def build(stage_id, window):
    return ReviewBody(window)
