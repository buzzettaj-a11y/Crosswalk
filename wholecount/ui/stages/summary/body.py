"""The Results body: held when stale, the status, the two goals, open pairs, automatic joins, programs, locations, people
and the printable page. Every number comes from the engine through the session; nothing is worked out here."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout, QLineEdit, QTextBrowser, QWidget

from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.pages import joins, pairs_page, people_page
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.bars import BarRow
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.pagebar import PageBar
from wholecount.ui.widgets.style import button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tonetag import BandWord, ToneTag

PAIRS_PAGE = 25
PEOPLE_PAGE = 100
PEOPLE_FIRST = 5
LOC_ROWS = (("high", "ink-2", False), ("low", "amber", False), ("not_mapped", "amber", True))
BREAKDOWN = ("no_fixed_address", "outside_nyc", "address_problem", "not_found", "no_geocoder")


def range_text(lo, hi):
    return f"{lo:,}" if lo == hi else copy.get("counts.range", low=lo, high=hi)


class ResultsBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        self.page_button = HeldAction("results.print_button", "secondary")
        self.page_button.setObjectName("openPrintable")
        self.page_button.clicked.connect(self.open_printable)
        self.cont = HeldAction("results.continue", "primary")
        self.cont.setObjectName("continueFiles")
        self.cont.clicked.connect(lambda: window.go_to("export"))
        window.run_hold.register(self.cont)
        self.head = StageHead("summary", [self.page_button, self.cont], saved_progress=v.saved_progress,
                              data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.body = vbox(spacing=16)
        lay.addLayout(self.body)
        lay.addStretch(1)
        self.pairs_open = False
        self.pairs_page = 0
        self.joins_open = False
        self.people_open = False
        self.people_page = 0
        self.join_reason = ""
        self.printable = None
        self.update_view(v)

    @property
    def session(self):
        return self.window_.bridge.session

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        clear(self.body)
        s = self.session
        stale = s is None or s.results is None or v.results_stale or v.counts is None or not v.counts.balance_ok
        if stale:
            hold = [HoldReason("results.hold_stale")]
            self.cont.set_holds(hold)
            self.page_button.set_holds(hold)
            c = Callout("wrong")
            c.setObjectName("resultsHeld")
            c.body.addWidget(label(copy.get("results.held_title"), role="row-title", tone="amber"))
            nothing = s is None or s.results is None
            c.body.addWidget(label(copy.get("review.not_run" if nothing else "results.held"), role="note", wrap=True))
            go = button(copy.get("results.go_process"), "primary", name="resultsGoProcess")
            go.clicked.connect(lambda: self.window_.go_to("run"))
            c.body.addWidget(go, 0, Qt.AlignLeft)
            self.body.addWidget(c)
            return
        self.cont.set_holds([])
        self.page_button.set_holds([])
        c = v.counts
        counts = s.results.counts
        self._status(c)
        self._goals(c, counts)
        self._pairs(c)
        self._joins()
        self._programs(counts)
        self._locations(c)
        self._people()

    # Status and goals

    def _status(self, c):
        f = Callout("ink" if c.is_final else "wrong")
        f.setObjectName("statusCallout")
        if c.is_final:
            top = hbox(spacing=8)
            top.addWidget(label(copy.get("results.final"), role="row-title", name="statusFinal"), 1)
            top.addWidget(ToneTag(copy.get("review.tag.settled"), "settled"))
            f.body.addLayout(top)
        else:
            if c.not_counted_yet:
                f.body.addWidget(label(copy.get("results.partial", n=c.not_counted_yet), role="note", wrap=True,
                                       name="statusPartial"))
            if c.open_pairs or c.open_copy_groups:
                key = "results.pairs_groups_open" if c.open_copy_groups else "results.pairs_open"
                f.body.addWidget(label(copy.get(key, n=c.open_pairs, g=c.open_copy_groups) if c.open_copy_groups
                                       else copy.get(key, n=c.open_pairs), role="note", wrap=True, name="statusPairs"))
        self.body.addWidget(f)

    def _goals(self, c, counts):
        row = hbox(spacing=14)
        for i, (rng, key) in enumerate(((c.goal1, "goal1"), (c.goal2, "goal2")), start=1):
            card = Callout("needs")
            card.setObjectName(f"goal{i}Card")
            card.body.addWidget(label(copy.get(f"results.{key}.kicker"), role="kicker"))
            card.body.addWidget(label(copy.get(f"results.{key}.title"), role="row-title"))
            card.body.addWidget(label(range_text(*rng), role="count-lg", name=f"goal{i}Number"))
            if rng[0] != rng[1]:
                until = (copy.get("results.until_groups", n=c.open_pairs, g=c.open_copy_groups) if c.open_copy_groups
                         else copy.get("results.until", n=c.open_pairs))
                card.body.addWidget(label(until, role="note", name=f"goal{i}Until"))
            card.body.addWidget(label(copy.get(f"results.{key}.body"), role="note", tone="ink-2", wrap=True))
            if key == "goal2":
                n = counts.people_without_program.high
                if n:
                    card.body.addWidget(label(copy.get("results.noprogram", n=n), role="note", wrap=True, name="noProgram"))
                for tp in self.window_.bridge.program_sources():
                    if tp.source == "none":
                        name = self.session.results.file_of_record.get(next((k for k, o in
                                                                             self.session.results.outcomes.items()
                                                                             if o.table_key == tp.table_key), ""), "")
                        card.body.addWidget(label(copy.get("results.no_program_file", file=name, n=tp.rows), role="caption",
                                                  wrap=True))
            row.addWidget(card, 1)
        self.body.addLayout(row)
        self.body.addWidget(label(copy.get("results.counted_from", a=c.counted, b=c.not_counted_yet, c=c.set_aside),
                                  role="note", name="countedFrom"))
        if counts.matched_from_earlier is not None:
            self.body.addWidget(label(copy.get("results.earlier", n=counts.matched_from_earlier), role="note",
                                      name="matchedEarlier"))

    # Pairs

    def _pairs(self, c):
        if not c.open_pairs and not self.pairs_open:
            return
        f = Callout("needs")
        f.setObjectName("pairsCallout")
        r = self.session.results
        auto = len(r.identity.auto_joins)
        by_person = sum(1 for d in self.session.decisions.of_kind("pair") if d.get("verdict") == "same")
        f.body.addWidget(label(copy.get("results.pairs.title", n=c.open_pairs), role="row-title"))
        f.body.addWidget(label(copy.get("results.pairs.line", a=auto, b=by_person), role="note", wrap=True))
        if not self.pairs_open:
            b = button(copy.get("results.pairs.decide"), "primary", name="decidePairs")
            b.clicked.connect(self._open_pairs)
            self.window_.run_hold.register(b)
            f.body.addWidget(b, 0, Qt.AlignLeft)
        else:
            items, total, pages = pairs_page(self.session, self.pairs_page, PAIRS_PAGE)
            for p in items:
                f.body.addWidget(self._pair_card(p))
            bar = PageBar(self.pairs_page, pages, PAIRS_PAGE, sizes=(PAIRS_PAGE,))
            bar.page_changed.connect(self._pairs_to)
            f.body.addWidget(bar)
        self.body.addWidget(f)

    def _open_pairs(self):
        self.pairs_open = True
        self.update_view(self.window_.view)

    def _pairs_to(self, p):
        self.pairs_page = p
        self.update_view(self.window_.view)

    def _pair_card(self, p):
        f = QFrame()
        f.setObjectName("pairCard")
        lay = vbox(f, (14, 10, 14, 10), 8)
        top = hbox(spacing=8)
        if p.band:
            top.addWidget(BandWord(copy.get(f"people.band.{p.band}")))
        top.addWidget(ToneTag(copy.get("results.pairs.decided" if p.decided else "results.pairs.needs"),
                              "decided" if p.decided else "needs_you"))
        top.addStretch(1)
        lay.addLayout(top)
        if p.decided:
            lay.addWidget(label(copy.get(f"results.pairs.was_{p.decided}"), role="note"))
            return f
        grid = QGridLayout()
        cols = ("source", "name", "dob", "address", "zip", "program", "id")
        for i, k in enumerate(cols):
            grid.addWidget(label(copy.get(f"results.pairs.col.{k}"), role="column-head"), 0, i)
        for r, row in enumerate(p.rows, start=1):
            for i, k in enumerate(cols):
                differs = p.rows[0][k] != p.rows[1][k]
                grid.addWidget(label(row[k], role="row-title" if differs else "note", tone="blue" if differs else None),
                               r, i)
        lay.addLayout(grid)
        if p.evidence:
            lay.addWidget(label(copy.get("results.pairs.agrees"), role="kicker"))
            lay.addWidget(label(" ".join(p.evidence), role="note", wrap=True))
        if p.cautions:
            lay.addWidget(label(copy.get("results.pairs.check"), role="kicker"))
            lay.addWidget(label(" ".join(p.cautions), role="note", wrap=True))
        row = hbox(spacing=8)
        same = button(copy.get("review.compare.same"), "primary", name=f"pairSame_{p.a}")
        diff = button(copy.get("review.compare.different"), "secondary", name=f"pairDifferent_{p.a}")
        same.clicked.connect(lambda _=False, p=p: self.decide(p, "same"))
        diff.clicked.connect(lambda _=False, p=p: self.decide(p, "different"))
        for b in (same, diff):
            self.window_.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        return f

    def decide(self, p, verdict):
        b = self.window_.bridge
        result = b.dispatch(C.DecidePair(p.a, p.b, verdict))
        if not result.ok and b.last_refusal == "second_signoff_needed":
            second = self.window_.ask_text(copy.get("review.second.title"), copy.get("results.pairs.second"))
            if second:
                b.dispatch(C.DecidePair(p.a, p.b, verdict, second))

    # Joins

    def _joins(self):
        r = self.session.results
        n = len(r.identity.auto_joins)
        box = Card()
        box.setObjectName("joinsCard")
        top = hbox(spacing=8)
        top.addWidget(label(copy.get("results.joins.title"), role="row-title"), 1)
        top.addWidget(label(f"{n:,}", role="row-title", name="joinsCount"))
        show = button(copy.get("src.show_them"), "quiet", "nav", name="showJoins")
        show.clicked.connect(self._toggle_joins)
        top.addWidget(show)
        box.body.addLayout(top)
        if self.joins_open:
            search = QLineEdit()
            search.setObjectName("joinSearch")
            search.setPlaceholderText(copy.get("results.joins.search"))
            box.body.addWidget(search)
            for j in joins(self.session, self.join_reason)[:200]:
                row = hbox(spacing=8)
                row.addWidget(label(j.master_id, role="caption"))
                row.addWidget(label(j.name, role="note"), 1)
                row.addWidget(label(copy.get("results.joins.records", n=j.records), role="caption"))
                row.addWidget(BandWord(copy.get("people.match.certain")))
                row.addWidget(label(copy.get(f"results.joins.reason.{j.reason}"), role="caption", wrap=True), 2)
                if len(j.persons) == 2:
                    sp = button(copy.get("review.compare.different"), "quiet", "nav", name=f"split_{j.master_id}")
                    sp.clicked.connect(lambda _=False, j=j: self.window_.bridge.dispatch(
                        C.DecidePair(j.persons[0], j.persons[1], "different")))
                    self.window_.run_hold.register(sp)
                    row.addWidget(sp)
                box.body.addLayout(row)
        self.body.addWidget(box)

    def _toggle_joins(self):
        self.joins_open = not self.joins_open
        self.update_view(self.window_.view)

    # Programs, locations and people

    def _programs(self, counts):
        box = Card()
        box.setObjectName("programsCard")
        box.body.addWidget(label(copy.get("results.programs.title"), role="row-title"))
        items = sorted(((p, r.low) for p, r in counts.per_program.items() if p), key=lambda x: -x[1])
        top = max([n for _, n in items] + [1])
        for p, n in items:
            box.body.addWidget(BarRow(p, n, n / top))
        none = counts.people_without_program.high
        if none:
            box.body.addWidget(BarRow(copy.get("results.programs.none"), none, none / top))
        box.body.addWidget(label(copy.get("results.programs.note"), role="caption"))
        self.body.addWidget(box)

    def _locations(self, c):
        loc = c.locations
        box = Card()
        box.setObjectName("locationsCard")
        box.body.addWidget(label(copy.get("results.loc.title"), role="row-title"))
        top = max(loc.high, loc.low, loc.not_mapped, 1)
        for key, tone, outline in LOC_ROWS:
            n = getattr(loc, key)
            box.body.addWidget(BarRow(copy.get(f"results.loc.{key}"), n, n / top, tone, outline))
        for k in BREAKDOWN:
            n = getattr(loc, k)
            if n > 0:
                r = hbox(margins=(16, 0, 0, 0), spacing=8)
                r.addWidget(label(copy.get(f"status.location.reason.{k}"), role="caption", name=f"breakdown_{k}"), 1)
                r.addWidget(label(f"{n:,}", role="caption"))
                box.body.addLayout(r)
        box.body.addWidget(label(copy.get("results.noaddr"), role="note", name="noAddrCounted"))
        if len(c.lines) > 1:
            k, p = c.lines[1]
            box.body.addWidget(label(copy.get(k, **p), role="note", tone="muted"))
        box.body.addWidget(label(copy.get("results.verified"), role="note", tone="muted"))
        self.body.addWidget(box)

    def _people(self):
        box = Card()
        box.setObjectName("peopleCard")
        box.body.addWidget(label(copy.get("results.people.title"), role="row-title"))
        size = PEOPLE_PAGE if self.people_open else PEOPLE_FIRST
        items, total, pages = people_page(self.session, self.people_page if self.people_open else 0, size)
        grid = QGridLayout()
        for i, k in enumerate(("person", "name", "programs", "counts_as")):
            grid.addWidget(label(copy.get(f"results.people.col.{k}"), role="column-head"), 0, i)
        for r, (m, name, progs) in enumerate(items, start=1):
            grid.addWidget(label(m, role="caption"), r, 0)
            grid.addWidget(label(name, role="note"), r, 1)
            grid.addWidget(label(", ".join(progs), role="note", wrap=True), r, 2)
            grid.addWidget(label(copy.get("results.people.counts_as", n=len(progs)), role="caption"), r, 3)
        grid.setColumnStretch(2, 1)
        box.body.addLayout(grid)
        if not self.people_open and total > PEOPLE_FIRST:
            row = hbox(spacing=8)
            row.addWidget(label(copy.get("results.people.more", n=total - PEOPLE_FIRST), role="note"), 1)
            more = button(copy.get("results.people.show"), "quiet", "nav", name="showPeople")
            more.clicked.connect(self._open_people)
            row.addWidget(more)
            box.body.addLayout(row)
        elif self.people_open:
            bar = PageBar(self.people_page, pages, PEOPLE_PAGE, sizes=(PEOPLE_PAGE,))
            bar.page_changed.connect(self._people_to)
            box.body.addWidget(bar)
        self.body.addWidget(box)

    def _open_people(self):
        self.people_open = True
        self.update_view(self.window_.view)

    def _people_to(self, p):
        self.people_page = p
        self.update_view(self.window_.view)

    # The printable page

    def open_printable(self):
        if self.page_button.held:
            return None
        self.printable = PrintablePage(self.window_)
        self.printable.open()
        return self.printable


class PrintablePage(QDialog):
    """A read-only view of the printable page, with Save as PDF and Save as a web page. Nothing is written before a save."""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.setModal(True)
        self.setFixedWidth(820)
        self.setMinimumHeight(640)
        lay = vbox(self, (20, 16, 20, 16), 10)
        lay.addWidget(label(copy.get("results.print.title"), role="h3"))
        self.browser = QTextBrowser()
        self.browser.setObjectName("printBrowser")
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        lay.addWidget(self.browser, 1)
        self.names = QCheckBox(copy.get("results.print.names"))
        self.names.setObjectName("includeFileNames")
        self.names.toggled.connect(self.draw)
        lay.addWidget(self.names)
        row = hbox(spacing=8)
        self.pdf = button(copy.get("results.print.pdf"), "primary", name="savePdf")
        self.web = button(copy.get("results.print.web"), "secondary", name="saveWeb")
        close = button(copy.get("drawer.close"), "quiet", "nav", name="printClose")
        self.pdf.clicked.connect(lambda: self.save_pdf())
        self.web.clicked.connect(lambda: self.save_web())
        close.clicked.connect(self.reject)
        for b in (self.pdf, self.web, close):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.draw()

    def html(self):
        return self.window_.bridge.summary_html(self.names.isChecked())

    def draw(self, *_):
        self.browser.setHtml(self.html())

    def _ask(self, filt):
        path, _ = QFileDialog.getSaveFileName(self, copy.get("results.print.title"), "", copy.get(filt))
        return path or None

    def save_pdf(self, path=None):
        from wholecount.ui.printable import save_pdf

        path = path or self._ask("results.print.pdf_filter")
        if path:
            save_pdf(self.html(), path)
        return path

    def save_web(self, path=None):
        path = path or self._ask("results.print.web_filter")
        if path:
            self.window_.bridge.save_summary(path, self.names.isChecked())
        return path


def build(stage_id, window):
    return ResultsBody(window)
