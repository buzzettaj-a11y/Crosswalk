"""Programs (SPEC 6.7, 11.5, board C2b_Program_Names): which column holds the program, which names are one program, and a
preview of the counts. Nothing is merged until the operator says so, and the preview decides nothing (A-07)."""
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLineEdit, QWidget

from wholecount import copy
from wholecount.session.commands import DecideProgramGroup, SetupChange, WithdrawProgramDecision
from wholecount.ui.frame import a11y
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.frame.view import PreviewView
from wholecount.ui.stages._common import Card, section_head, source_label
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.style import narrow_combo, button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tag import tag
from wholecount.ui.widgets.help import HelpButton, titled

ONE_NAME = "__one_name__"
NO_COLUMN = "__none__"


class ProgramsBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=18)
        self.cont = HeldAction("prog.continue", "primary")
        self.cont.setObjectName("continueProcess")
        self.cont.clicked.connect(lambda: window.go_to("run"))
        self.head = StageHead("programs", [self.cont], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.notice = vbox(spacing=6)
        lay.addLayout(self.notice)
        lead = Callout("needs")
        lead.body.addWidget(label(copy.get("prog.lead.title"), role="row-title"))
        lead.body.addWidget(label(copy.get("prog.lead.body"), role="note", wrap=True))
        lay.addWidget(lead)
        self.s1 = vbox(spacing=8)
        self.s2 = vbox(spacing=10)
        self.s3 = vbox(spacing=8)
        for s in (self.s1, self.s2, self.s3):
            lay.addLayout(s)
        lay.addStretch(1)
        self.holding = None
        self.one_name_open = set()
        self.show_singles = False
        self.update_view(v)

    def sv(self):
        return self.window_.bridge.survey()

    def dispatch(self, cmd):
        if not self.window_.run_hold.active:
            self.window_.bridge.dispatch(cmd)

    # Section 1

    def _section1(self, sv):
        clear(self.s1)
        self.s1.addWidget(section_head(1, copy.get("prog.s1.title")))
        if sv is None:
            return
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        for i, k in enumerate(("source", "column", "holds")):
            grid.addWidget(label(copy.get(f"prog.s1.col.{k}"), role="column-head"), 0, i)
        tps = {tp.table_key: tp for tp in sv.program_tables}
        r = 1
        for key, w in sv.works.items():
            t = sv.table(key)
            tp = tps.get(key)
            grid.addWidget(source_label(t.letter, t.file_name, role="note"), r, 0)
            cb = QComboBox()
            narrow_combo(cb)
            cb.setObjectName(f"programColumn_{t.letter}_{t.idx}")
            cb.setFixedWidth(230)
            cols = [p.column for p in w.profiles]
            ordered = sorted(cols, key=lambda c: (self._bad_for_program(w, c.name), c.index))
            for c in ordered:
                cb.addItem(c.name, c.name)
            cb.addItem(copy.get("prog.s1.none"), NO_COLUMN)
            cb.addItem(copy.get("prog.s1.one_name"), ONE_NAME)
            cur = w.mapping.column_for("Program")
            if tp is not None and tp.source == "none":
                cb.setCurrentIndex(cb.findData(NO_COLUMN))
            elif tp is not None and tp.source == "default" or key in self.one_name_open:
                cb.setCurrentIndex(cb.findData(ONE_NAME))
            elif cur is not None:
                cb.setCurrentIndex(cb.findData(cur.name))
            cb.activated.connect(lambda _, cb=cb, t=t: self.set_column(t, cb.currentData()))
            self.window_.run_hold.register(cb)
            grid.addWidget(cb, r, 1)
            holds = vbox(spacing=4)
            if tp is not None and tp.source == "column":
                names = [n for n, _ in sorted(tp.values, key=lambda x: -x[1]) if n][:3]
                holds.addWidget(label(" · ".join(names), role="note"))
                chk = w.mapping.checks.get("Program")
                if chk is not None and chk.reason_id == "col_program_looks_like_codes":
                    row = QFrame()
                    row.setObjectName("amberRow")
                    rl = vbox(row, (10, 6, 10, 6), 4)
                    rl.addWidget(label(copy.get("prog.s1.codes", a=(names + ["", "", ""])[0], b=(names + ["", "", ""])[1],
                                                c=(names + ["", "", ""])[2]), role="note", tone="amber", wrap=True))
                    if chk.better is not None:
                        rl.addWidget(label(copy.get("prog.s1.better", column=chk.better.name), role="note", wrap=True))
                        use = button(copy.get("map.use", column=chk.better.name), "primary", name=f"progUse_{t.letter}")
                        use.clicked.connect(lambda _=False, t=t, c=chk.better.name: self.set_column(t, c))
                        self.window_.run_hold.register(use)
                        rl.addWidget(use, 0, Qt.AlignLeft)
                    holds.addWidget(row)
            elif tp is not None and tp.source == "default":
                holds.addWidget(label(tp.default or "", role="note"))
            else:
                row = QFrame()
                row.setObjectName("amberRow")
                rl = vbox(row, (10, 6, 10, 6), 4)
                rl.addWidget(label(copy.get("prog.s1.no_column", n=t.rows), role="note", tone="amber", wrap=True,
                                   name=f"noProgram_{t.letter}"))
                holds.addWidget(row)
            if key in self.one_name_open or (tp is not None and tp.source == "default"):
                e = QLineEdit(self.window_.bridge.session.setup.get("defaults", (t.file_name, t.idx, "Program")) or "")
                e.setObjectName(f"programDefault_{t.letter}")
                e.setPlaceholderText(copy.get("prog.s1.one_name_placeholder"))
                e.editingFinished.connect(lambda e=e, t=t: e.text().strip() and self.dispatch(
                    SetupChange("defaults", (t.file_name, t.idx, "Program"), e.text().strip())))
                self.window_.run_hold.register(e)
                holds.addWidget(e)
            grid.addLayout(holds, r, 2)
            r += 1
        grid.setColumnStretch(2, 1)
        self.s1.addLayout(grid)

    def _bad_for_program(self, w, name):
        p = next((p for p in w.profiles if p.column.name == name), None)
        if p is None or not p.n_values:
            return True
        return p.date_share > 0.5 or p.share("digits") > 0.5

    def set_column(self, t, choice):
        session = self.window_.bridge.session
        override = session.setup.get("program_columns", (t.file_name, t.idx))
        if choice == ONE_NAME:
            self.one_name_open.add(t.key)
            self._section1(self.sv())
            return
        self.one_name_open.discard(t.key)
        if choice == NO_COLUMN:
            self.dispatch(SetupChange("program_columns", (t.file_name, t.idx), "none"))
            return
        if override == "none":
            self.dispatch(SetupChange("program_columns", (t.file_name, t.idx), None))
        self.dispatch(SetupChange("mappings", (t.file_name, t.idx, "Program"), choice))

    # Section 2

    def _letters(self, sv, name):
        keys = getattr(name, "tables", ()) or ()
        letters = sorted({sv.table(k).letter for k in keys if any(t.key == k for t in sv.tables)})
        return "".join(letters)

    def _section2(self, sv):
        clear(self.s2)
        if sv is None:
            return
        names = {n.name: n for n in sv.program_names}
        pm = sv.program_map
        groups = []
        for p in pm.unconfirmed:
            groups.append(("proposal", p.label, tuple(p.members), p))
        for g in pm.groups:
            groups.append(("confirmed", g.label, tuple(g.members), g))
        grouped = {m for _, _, ms, _ in groups for m in ms}
        singles = [n for n in sorted(names) if n not in grouped]
        files = len(sv.works)
        reset = button(copy.get("prog.s2.reset"), "quiet", "nav", name="resetPrograms")
        reset.clicked.connect(self.reset)
        self.window_.run_hold.register(reset)
        self.s2.addWidget(section_head(2, copy.get("prog.s2.title"),
                                       copy.get("prog.s2.note", n=len(names), m=files, k=len(groups) + len(singles)), reset))
        self.s2.addLayout(titled(label(copy.get("help.el.program_groups.title"), role="caption"), "el.program_groups"))
        if self.holding:
            bar = QFrame()
            bar.setObjectName("holdingBar")
            bl = hbox(bar, (12, 8, 12, 8), 8)
            bl.addWidget(label(copy.get("prog.s2.holding", name=self.holding), role="note"))
            own = button(copy.get("prog.s2.own"), "quiet", "nav", name="countOwn")
            own.clicked.connect(self.count_on_own)
            back = button(copy.get("prog.s2.put_back"), "quiet", "nav", name="putBack")
            back.clicked.connect(self.put_back)
            for x in (own, back):
                self.window_.run_hold.register(x)
                bl.addWidget(x)
            bl.addStretch(1)
            self.s2.addWidget(bar)
        for kind, lbl, members, obj in groups:
            self.s2.addWidget(self._group_card(sv, kind, lbl, members, obj, names))
        if singles:
            row = hbox(spacing=8)
            row.addWidget(label(copy.get("prog.s2.singles", n=len(singles), names=", ".join(singles[:6])), role="note",
                                wrap=True), 1)
            more = button(copy.get("src.show_them"), "quiet", "nav", name="showSingles")
            more.clicked.connect(self._toggle_singles)
            row.addWidget(more)
            self.s2.addLayout(row)
            if self.show_singles or self.holding:
                for n in singles:
                    self.s2.addWidget(self._group_card(sv, "single", n, (n,), None, names))

    def _toggle_singles(self):
        self.show_singles = not self.show_singles
        self._section2(self.sv())

    def _group_card(self, sv, kind, lbl, members, obj, names):
        c = QFrame()
        c.setObjectName("programGroup")
        set_prop(c, "callout", "needs" if kind == "proposal" else "decided" if kind == "confirmed" else "ink")
        lay = vbox(c, (16, 12, 16, 12), 8)
        top = hbox(spacing=10)
        name = QLineEdit(lbl)
        name.setObjectName(f"groupName_{lbl}")
        name.setFixedWidth(300)
        name.setAccessibleName(copy.get("prog.s2.group_name"))
        if kind != "single":
            name.editingFinished.connect(lambda n=name, ms=members, old=lbl: n.text().strip() and n.text().strip() != old
                                         and self.dispatch(DecideProgramGroup("rename", ms, n.text().strip())))
        else:
            name.setReadOnly(True)
        self.window_.run_hold.register(name)
        top.addWidget(name)
        rows = sum(names[m].rows for m in members if m in names)
        top.addWidget(label(copy.get("prog.s2.rows", rows=rows, n=len({ch for m in members if m in names
                                                                          for ch in self._letters(sv, names[m])}) or 1),
                            role="caption"))
        if kind == "proposal":
            top.addWidget(tag(copy.get("prog.s2.needs"), "needs"))
        elif kind == "confirmed":
            top.addWidget(tag(copy.get("prog.s2.confirmed"), "confirmed"))
            if getattr(obj, "from_earlier_batch", False):
                top.addWidget(tag(copy.get("prog.s2.earlier"), "neutral"))
        top.addStretch(1)
        if self.holding and self.holding not in members:
            here = button(copy.get("prog.s2.move_here", name=self.holding.upper()), "secondary", name=f"moveHere_{lbl}")
            here.clicked.connect(lambda _=False, ms=members, l=lbl: self.move_to(ms, l))
            self.window_.run_hold.register(here)
            top.addWidget(here)
        lay.addLayout(top)
        chips = hbox(spacing=6)
        for m in members:
            n = names.get(m)
            chip = button(copy.get("prog.s2.chip", name=m, rows=n.rows if n else 0, letters=self._letters(sv, n) if n else ""),
                          "chip", name=f"chip_{m}")
            set_prop(chip, "held_chip", m == self.holding)
            if m == self.holding:
                chip.setText(chip.text() + " · " + copy.get("prog.s2.held"))
            chip.clicked.connect(lambda _=False, m=m, ms=members: self.pick(m, ms))
            self.window_.run_hold.register(chip)
            chips.addWidget(chip)
        chips.addStretch(1)
        lay.addLayout(chips)
        if kind == "proposal":
            reasons = getattr(obj, "reasons", ())
            if reasons:
                a, b, code = reasons[0]
                lay.addWidget(label(copy.get(f"prog.reason.{code}", a=a, b=b), role="note", wrap=True))
            row = hbox(spacing=8)
            yes = button(copy.get("prog.s2.one"), "primary", name=f"confirm_{lbl}")
            yes.clicked.connect(lambda _=False, ms=members, l=lbl: self.dispatch(DecideProgramGroup("confirm", ms, l)))
            no = button(copy.get("prog.s2.separate"), "secondary", name=f"separate_{lbl}")
            no.clicked.connect(lambda _=False, ms=members: self.dispatch(DecideProgramGroup("split", ms)))
            for x in (yes, no):
                self.window_.run_hold.register(x)
                row.addWidget(x)
            row.addWidget(label(copy.get("prog.s2.recorded"), role="caption"))
            row.addStretch(1)
            lay.addLayout(row)
        elif kind == "confirmed":
            dec = self._decision_for(members)
            if dec is not None:
                undo = button(copy.get("prog.s2.undo"), "quiet", "nav", name=f"undoGroup_{lbl}")
                undo.clicked.connect(lambda _=False, d=dec: self.dispatch(WithdrawProgramDecision(d.decision_id)))
                self.window_.run_hold.register(undo)
                lay.addWidget(undo, 0, Qt.AlignLeft)
        return c

    def _decision_for(self, members):
        for d in sorted(self.window_.bridge.session.decisions.of_kind("program"), key=lambda d: d.made_at, reverse=True):
            if set(d.all("program")) & set(members) and d.get("program_kind") in ("confirm", "merge"):
                return d
        return None

    def pick(self, name, members):
        if self.window_.run_hold.active:
            return
        if self.holding == name:
            self.put_back()
            return
        if self.holding and self.holding not in members:
            self.move_to(members, None)
            return
        self.holding = name
        a11y.announce(copy.get("prog.s2.picked", name=name))
        self._section2(self.sv())

    def move_to(self, members, lbl):
        name, self.holding = self.holding, None
        a11y.announce(copy.get("prog.s2.moved", name=name))
        self.dispatch(DecideProgramGroup("merge", tuple(members) + (name,), lbl if lbl and lbl not in (name,) else None))

    def count_on_own(self):
        name, self.holding = self.holding, None
        a11y.announce(copy.get("prog.s2.moved", name=name))
        self.dispatch(DecideProgramGroup("split", (name,)))

    def put_back(self):
        name, self.holding = self.holding, None
        a11y.announce(copy.get("prog.s2.put_down", name=name))
        self._section2(self.sv())

    def reset(self):
        w = self.window_
        if not w.confirm(copy.get("prog.s2.reset_title"), (copy.get("prog.s2.reset_q"),), copy.get("prog.s2.reset"),
                         copy.get("close.keep")):
            return
        for d in list(w.bridge.session.decisions.of_kind("program")):
            self.dispatch(WithdrawProgramDecision(d.decision_id))

    # Section 3

    def _section3(self, sv):
        clear(self.s3)
        self.s3.addWidget(section_head(3, copy.get("prog.s3.title")))
        prev = self.window_.bridge.ui.get("program_preview")
        stale = prev is not None and prev["key"] != self._preview_key()
        c = QFrame()
        set_prop(c, "callout", "wrong" if stale else "ink")
        c.setObjectName("previewCard")
        lay = vbox(c, (16, 14, 16, 14), 8)
        lay.addWidget(label(copy.get("prog.s3.card"), role="row-title"))
        if stale:
            lay.addWidget(label(copy.get("prog.s3.stale", time=prev["time"]), role="note", tone="amber", wrap=True,
                                name="previewStale"))
        self.refresh_btn = HeldAction("prog.s3.refresh", "primary")
        self.refresh_btn.setObjectName("refreshPreview")
        self.refresh_btn.clicked.connect(self.refresh_preview)
        self.window_.run_hold.register(self.refresh_btn)
        lay.addWidget(self.refresh_btn, 0, Qt.AlignLeft)
        if prev is None:
            lay.addWidget(label(copy.get("prog.s3.none"), role="note", name="previewNone"))
        else:
            counts = prev["counts"]
            boxes = hbox(spacing=12)
            for k, rng, text in (("goal1", counts.goal1, copy.get("prog.s3.goal1_note", lo=counts.goal1.low,
                                                                  hi=counts.goal1.high)),
                                 ("goal2", counts.goal2, copy.get("prog.s3.goal2_note"))):
                b = Card()
                b.body.addWidget(label(copy.get(f"prog.s3.{k}"), role="kicker"))
                b.body.addWidget(label(f"{rng.low:,}" if rng.low == rng.high else copy.get("counts.range", low=rng.low,
                                                                                        high=rng.high),
                                       role="count", name=f"preview_{k}"))
                b.body.addWidget(label(text, role="note", wrap=True))
                boxes.addWidget(b, 1)
            lay.addLayout(boxes)
            table = QGridLayout()
            for i, k in enumerate(("program", "clients", "rows")):
                table.addWidget(label(copy.get(f"prog.s3.col.{k}"), role="column-head"), 0, i)
            rowsof = {}
            for n in (sv.program_names if sv else ()):
                lab = sv.program_map.alias.get(n.name, n.name)
                rowsof[lab] = rowsof.get(lab, 0) + n.rows
            unconfirmed = {m: p.label for p in (sv.program_map.unconfirmed if sv else ()) for m in p.members}
            for r, (prog, rng) in enumerate(sorted(counts.per_program.items()), start=1):
                name = prog or copy.get("prog.s3.no_program")
                cell = vbox(spacing=2)
                cell.addWidget(label(name, role="note"))
                if prog in unconfirmed and unconfirmed[prog] != prog:
                    cell.addWidget(label(copy.get("prog.s3.apart", group=unconfirmed[prog]), role="caption", tone="amber"))
                table.addLayout(cell, r, 0)
                table.addWidget(label(f"{rng.low:,}", role="note"), r, 1)
                table.addWidget(label(f"{rowsof.get(prog, 0):,}", role="note"), r, 2)
            lay.addLayout(table)
            lay.addWidget(label(copy.get("prog.s3.foot", n=counts.counted, m=counts.not_counted_yet), role="caption",
                                wrap=True))
        self.s3.addWidget(c)

    def _preview_key(self):
        s = self.window_.bridge.session
        fp = s.live_fingerprints()
        return fp["programs"]

    def refresh_preview(self):
        from wholecount.ui.jobs.actions import PreviewJob

        w = self.window_
        key = self._preview_key()
        when = w.clock().astimezone(dt.timezone.utc).strftime("%H:%M")

        def done(counts):
            w.bridge.ui["program_preview"] = {"counts": counts, "key": key, "time": when}
            w.bridge.ui["preview_view"] = PreviewView(counts.goal1.low, counts.goal2.low, when)
        w.start_job(PreviewJob(w.bridge.session, done))

    def update_view(self, v):
        sv = self.sv()
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        n = len(sv.program_map.unconfirmed) if sv and sv.program_map else 0
        self.cont.set_holds([HoldReason("prog.hold", {"n": n})] if n else [])
        clear(self.notice)
        if self.window_.program_notice:
            self.notice.addWidget(label(copy.get("src.fast.programs", n=self.window_.program_notice), role="note",
                                        tone="blue", wrap=True, name="programNotice"))
        self._section1(sv)
        self._section2(sv)
        self._section3(sv)


def build(stage_id, window):
    return ProgramsBody(window)
