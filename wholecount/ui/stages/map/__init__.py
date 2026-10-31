"""Match your columns (SPEC 6.2, 11.5, board C2_Matching): a table list, a field grid with the column check and its
one-click fix, date order, the two-digit year rule, defaults for one source, and the blocked run band."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLineEdit, QSpinBox, QWidget

from wholecount import copy
from wholecount.session.commands import ConfirmTable, SetKeepSensitive, SetupChange
from wholecount.session.map_edit import with_order, with_pivot
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card, source_label
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import narrow_combo, button, clear, hbox, label, set_prop, vbox

LIST_WIDTH = 236
BLOCK_LINES = 3


def check_text(chk):
    return copy.get(f"mapping.check.{chk.reason_id}", **chk.params)


class MapBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        go = button(copy.get("map.continue"), "primary", name="continuePrograms")
        go.clicked.connect(lambda: window.go_to("programs"))
        self.head = StageHead("map", [go], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.band = vbox(spacing=8)
        lay.addLayout(self.band)
        self.check_callout = vbox(spacing=8)
        lay.addLayout(self.check_callout)
        cols = hbox(spacing=16)
        self.tables_col = QWidget()
        self.tables_col.setFixedWidth(LIST_WIDTH)
        self.tables = vbox(self.tables_col, spacing=6)
        cols.addWidget(self.tables_col, 0, Qt.AlignTop)
        right = vbox(spacing=12)
        self.grid_box = QWidget()
        self.grid = QGridLayout(self.grid_box)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(14)
        right.addWidget(self.grid_box)
        right.addLayout(self._actions())
        self.defaults_box = vbox(spacing=8)
        right.addLayout(self.defaults_box)
        cols.addLayout(right, 1)
        lay.addLayout(cols)
        lay.addWidget(self._promo())
        self.footer = label("", role="note", wrap=True, name="unmappedLine")
        lay.addWidget(self.footer)
        lay.addStretch(1)
        self.selected = None
        self.show_defaults = False
        self.focus_field = None
        self.update_view(v)

    # Data

    def sv(self):
        return self.window_.bridge.survey()

    def work(self):
        sv = self.sv()
        if sv is None or not sv.works:
            return None
        if self.selected not in sv.works:
            self.selected = next(iter(sv.works))
        return sv.works[self.selected]

    def facts(self, key=None):
        return self.sv().table(key or self.selected)

    def set_mapping(self, field_key, column):
        f = self.facts()
        self.window_.bridge.dispatch(SetupChange("mappings", (f.file_name, f.idx, field_key), column or ""))

    # Regions

    def _band(self, sv):
        clear(self.band)
        blocks = list(sv.blocks) if sv else []
        if not blocks:
            return
        c = Callout("wrong")
        c.setObjectName("blockedBand")
        c.body.addWidget(label(copy.get("map.band.title"), role="row-title", tone="amber"))
        for b in blocks[:BLOCK_LINES]:
            t = sv.table(b.table_key)
            row = hbox(spacing=8)
            if b.kind == "ssn_shaped_id":
                row.addWidget(label(copy.get("map.ssn"), role="note", wrap=True), 1)
                other = button(copy.get("map.band.other"), "primary", name="matchOther")
                other.clicked.connect(lambda _=False, b=b: self.select(b.table_key, b.field))
                col = sv.work(b.table_key).mapping.column_for(b.field)
                drop = button(copy.get("map.band.drop"), "secondary", name="dropColumn")
                drop.clicked.connect(lambda _=False, col=col: self.drop_column(col))
                for x in (other, drop):
                    self.window_.run_hold.register(x)
                    row.addWidget(x)
            else:
                row.addWidget(label(copy.get("map.band.line", table=t.file_name, field=b.field), role="note", wrap=True), 1)
                fix = button(copy.get("map.band.match_it"), "primary", name=f"matchIt_{b.field}")
                fix.clicked.connect(lambda _=False, b=b: self.select(b.table_key, b.field))
                row.addWidget(fix)
            c.body.addLayout(row)
        self.band.addWidget(c)

    def drop_column(self, col):
        """Drop an SSN-shaped column: the file is read again without it, as unticking it on Add your files does. Such a
        column is only present because it was kept at load, so dropping it ends the keep."""
        if col is not None:
            self.window_.bridge.dispatch(SetKeepSensitive(col.name, False))

    def _check_callout(self, sv):
        clear(self.check_callout)
        n = sum(1 for w in (sv.works.values() if sv else ()) for c in w.mapping.checks.values() if c.status == "problem")
        if not n:
            return
        c = Callout("wrong")
        c.setObjectName("checkCallout")
        c.body.addWidget(label(copy.get("map.check.title", n=n), role="row-title", tone="amber"))
        c.body.addWidget(label(copy.get("map.check.body"), role="note", wrap=True))
        self.check_callout.addWidget(c)

    def _tables(self, sv):
        clear(self.tables)
        self.tables.addWidget(label(copy.get("map.tables").upper(), role="kicker"))
        for key, w in (sv.works.items() if sv else ()):
            t = sv.table(key)
            wrong = sum(1 for c in w.mapping.checks.values() if c.status == "problem")
            state = copy.get("map.state.confirmed") if t.name in self.window_.bridge.session.confirmed_tables \
                else copy.get("map.state.mapped")
            b = button("", "secondary", name=f"table_{t.letter}_{t.idx}")
            inner = vbox(b, (10, 6, 10, 6), 2)
            for x in (source_label(t.letter, t.file_name, role="note"),
                      label(copy.get("map.table_line", rows=t.rows, wrong=wrong, state=state), role="caption")):
                x.setAttribute(Qt.WA_TransparentForMouseEvents)
                inner.addWidget(x)
            b.setMinimumHeight(56)
            b.setAccessibleName(t.file_name)
            set_prop(b, "selected", key == self.selected)
            set_prop(b, "kind", "chip")
            b.clicked.connect(lambda _=False, k=key: self.select(k))
            self.tables.addWidget(b)
        self.tables.addStretch(1)

    def select(self, key, field_key=None):
        self.selected = key
        self.focus_field = field_key
        self.update_view(self.window_.view)

    def _fields(self, sv):
        clear(self.grid)
        self.combos = {}
        w = self.work()
        if w is None:
            self.grid.addWidget(label(copy.get("schema.fit.none"), role="note"), 0, 0)
            return
        schema = self.window_.bridge.session.schema()
        profiles = {p.column.name: p for p in w.profiles}
        cols_real = [p.column for p in w.profiles if not p.column.derived]
        cols_made = [p.column for p in w.profiles if p.column.derived]
        for i, f in enumerate(schema.enabled_fields()):
            box = QWidget()
            bl = vbox(box, spacing=4)
            head = label(f.key + (copy.get("map.required_suffix") if f.required else ""), role="row-title", wrap=True)
            bl.addWidget(head)
            cb = QComboBox()
            narrow_combo(cb)
            cb.setObjectName(f"field_{f.key}")
            cb.setAccessibleName(f.key)
            cb.addItem(copy.get("map.none"), "")
            for c in cols_real:
                cb.addItem(c.name, c.name)
            if cols_made:
                cb.insertSeparator(cb.count())
                cb.addItem(copy.get("map.made_on_tidy"), None)
                cb.model().item(cb.count() - 1).setEnabled(False)
                for c in cols_made:
                    cb.addItem(c.name, c.name)
            cur = w.mapping.column_for(f.key)
            cb.setCurrentIndex(max(0, cb.findData(cur.name if cur else "")))
            cb.activated.connect(lambda _, cb=cb, k=f.key: self.set_mapping(k, cb.currentData()))
            self.window_.run_hold.register(cb)
            bl.addWidget(cb)
            note = copy.get(f"map.note.{f.key.lower()}") if f.builtin else copy.get("schema.handling.custom")
            bl.addWidget(label(note, role="micro", wrap=True))
            prof = profiles.get(cur.name) if cur is not None else None
            ssn_like = prof is not None and prof.counts.get("ssn", 0) * 2 > prof.n_values
            if prof is not None and prof.samples and not ssn_like:      # never show SSN-shaped values (P-MAP-7)
                s = list(profiles[cur.name].samples)[:3] + ["", "", ""]
                bl.addWidget(label(copy.get("map.samples", a=s[0], b=s[1], c=s[2]), role="micro", tone="muted", wrap=True))
            chk = w.mapping.checks.get(f.key)
            if chk is not None and chk.status == "problem":
                set_prop(cb, "check", "problem")
                c = Callout("wrong")
                c.setObjectName(f"check_{f.key}")
                c.body.addWidget(label(check_text(chk), role="caption", tone="amber", wrap=True))
                if chk.better is not None:
                    use = button(copy.get("map.use", column=chk.better.name), "primary", name=f"use_{f.key}")
                    use.clicked.connect(lambda _=False, k=f.key, col=chk.better.name: self.set_mapping(k, col))
                    self.window_.run_hold.register(use)
                    c.body.addWidget(use, 0, Qt.AlignLeft)
                bl.addWidget(c)
            if f.key == "Date_of_Birth" or f.type.value == "date":
                self._date_rows(bl, f.key)
            self.grid.addWidget(box, i // 3, i % 3, Qt.AlignTop)
            self.combos[f.key] = cb
        if self.focus_field in self.combos:
            self.combos[self.focus_field].setFocus(Qt.OtherFocusReason)

    def _date_rows(self, bl, field_key):
        sv = self.sv()
        entry = sv.dates.get((self.selected, field_key))
        if entry is None:
            return
        ev, dec, setting = entry
        bl.addWidget(label(copy.get("map.date.counts", a=ev.month_first_only, b=ev.day_first_only, c=ev.either),
                           role="micro", name=f"dateCounts_{field_key}", wrap=True))
        f = self.facts()
        key = (f.file_name, f.idx, field_key)
        if dec.state in ("ask_both_ways", "ask_no_evidence") and not dec.answered:
            c = Callout("wrong")
            c.setObjectName(f"dateAsk_{field_key}")
            c.body.addWidget(label(copy.get("map.date.ask"), role="caption", tone="amber", wrap=True))
            row = hbox(spacing=6)
            for order, text in (("month_first", "map.date.month_first"), ("day_first", "map.date.day_first")):
                b = button(copy.get(text), "primary" if order == "month_first" else "secondary", name=f"{order}_{field_key}")
                b.clicked.connect(lambda _=False, o=order: self.window_.bridge.dispatch(
                    SetupChange("date_orders", key, with_order(setting, o))))
                self.window_.run_hold.register(b)
                row.addWidget(b)
            c.body.addLayout(row)
            c.body.addWidget(label(copy.get("map.date.until"), role="micro"))
            bl.addWidget(c)
        sel = QComboBox()
        narrow_combo(sel)
        sel.setObjectName(f"twoDigit_{field_key}")
        sel.addItem(copy.get("map.two_digit.review"), "review")
        sel.addItem(copy.get("map.two_digit.rule"), "rule")
        pivot = setting.pivot.pivot if setting and setting.pivot else None
        sel.setCurrentIndex(1 if pivot is not None or self._rule_open.get((self.selected, field_key)) else 0)
        self.window_.run_hold.register(sel)
        bl.addWidget(label(copy.get("map.two_digit.label"), role="micro"))
        bl.addWidget(sel)
        sel.activated.connect(lambda _: self._two_digit_mode(field_key, key, setting, sel.currentData()))
        if sel.currentData() == "rule":
            row = hbox(spacing=6)
            row.addWidget(label(copy.get("map.two_digit.up_to"), role="caption"))
            box = QSpinBox()
            box.setObjectName(f"pivot_{field_key}")
            box.setRange(-1, 99)
            box.setSpecialValueText(" ")
            box.setValue(pivot if pivot is not None else -1)
            box.editingFinished.connect(lambda: box.value() >= 0 and self.window_.bridge.dispatch(
                SetupChange("date_orders", key, with_pivot(setting, box.value()))))
            self.window_.run_hold.register(box)
            row.addWidget(box)
            row.addStretch(1)
            bl.addLayout(row)
            suggest = sv.pivots.get((self.selected, field_key))
            if suggest is not None and pivot is None:
                use = button(copy.get("map.two_digit.use", nn=f"{suggest:02d}"), "quiet", "nav", name=f"usePivot_{field_key}")
                use.clicked.connect(lambda _=False: self.window_.bridge.dispatch(
                    SetupChange("date_orders", key, with_pivot(setting, suggest))))
                self.window_.run_hold.register(use)
                bl.addWidget(use, 0, Qt.AlignLeft)
            if pivot is not None and pivot < 99:
                bl.addWidget(label(copy.get("map.two_digit.example", nn=f"{pivot:02d}", y1=2000 + pivot,
                                            next=f"{pivot + 1:02d}", y2=1900 + pivot + 1), role="micro",
                                   name=f"pivotExample_{field_key}"))

    def _two_digit_mode(self, field_key, key, setting, mode):
        if mode == "review":
            self._rule_open[(self.selected, field_key)] = False
            if setting and setting.pivot:
                self.window_.bridge.dispatch(SetupChange("date_orders", key, with_pivot(setting, None)))
                return
        else:
            self._rule_open[(self.selected, field_key)] = True
        self._fields(self.sv())

    def _actions(self):
        row = hbox(spacing=8)
        self.confirm = HeldAction("map.confirm", "primary")
        self.confirm.setObjectName("confirmTable")
        self.confirm.clicked.connect(self.confirm_table)
        self.window_.run_hold.register(self.confirm)
        show = button(copy.get("src.show_data"), "secondary", name="mapShowData")
        show.clicked.connect(lambda: self.selected and self.window_.show_data(self.selected))
        fill = button(copy.get("map.fill_link"), "quiet", "nav", name="fillLink")
        fill.clicked.connect(self.toggle_defaults)
        self.all_confirmed = label("", role="note", name="allConfirmed")
        for x in (self.confirm, show, fill):
            row.addWidget(x)
        row.addWidget(self.all_confirmed)
        row.addStretch(1)
        return row

    def confirm_table(self):
        sv = self.sv()
        f = self.facts()
        self.window_.bridge.dispatch(ConfirmTable(f.name))
        done = self.window_.bridge.session.confirmed_tables
        left = [k for k in sv.works if sv.table(k).name not in done]
        if left:
            self.select(left[0])
        else:
            self.all_confirmed.setText(copy.get("map.all_confirmed", n=len(sv.works)))

    def toggle_defaults(self):
        self.show_defaults = not self.show_defaults
        self._defaults()

    def _defaults(self):
        clear(self.defaults_box)
        w = self.work()
        if not self.show_defaults or w is None:
            return
        f = self.facts()
        c = Card()
        c.setObjectName("defaultsCard")
        c.body.addWidget(label(copy.get("map.defaults.title"), role="row-title"))
        c.body.addWidget(label(copy.get("map.defaults.note"), role="note", wrap=True))
        setup = self.window_.bridge.session.setup
        for fld in self.window_.bridge.session.schema().enabled_fields():
            if w.mapping.column_for(fld.key) is not None:
                continue
            row = hbox(spacing=8)
            row.addWidget(label(fld.key, role="note"), 1)
            e = QLineEdit(setup.get("defaults", (f.file_name, f.idx, fld.key)) or "")
            e.setObjectName(f"default_{fld.key}")
            e.setPlaceholderText(copy.get("map.defaults.placeholder"))
            e.editingFinished.connect(lambda e=e, k=fld.key: self.window_.bridge.dispatch(
                SetupChange("defaults", (f.file_name, f.idx, k), e.text().strip() or None))
                if (e.text().strip() or None) != setup.get("defaults", (f.file_name, f.idx, k)) else None)
            self.window_.run_hold.register(e)
            row.addWidget(e, 2)
            c.body.addLayout(row)
        self.defaults_box.addWidget(c)

    def _promo(self):
        c = Card()
        c.setObjectName("programsPromo")
        c.body.addWidget(label(copy.get("map.promo.title"), role="row-title"))
        c.body.addWidget(label(copy.get("map.promo.body"), role="note", wrap=True))
        go = button(copy.get("map.promo.go"), "secondary", name="goPrograms")
        go.clicked.connect(lambda: self.window_.go_to("programs"))
        c.body.addWidget(go, 0, Qt.AlignLeft)
        return c

    def _footer(self):
        w = self.work()
        if w is None:
            self.footer.setText("")
            return
        mapped = {a.column.name for a in w.mapping.assignments}
        unmapped = [p.column.name for p in w.profiles if p.column.name not in mapped and not p.column.derived]
        text = copy.get("map.footer")
        if unmapped:
            text += " " + copy.get("map.footer_names", names=", ".join(unmapped))
        self.footer.setText(text)

    def update_view(self, v):
        if not hasattr(self, "_rule_open"):
            self._rule_open = {}
        sv = self.sv()
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        self._band(sv)
        self._check_callout(sv)
        self.work()
        self._tables(sv)
        self._fields(sv)
        self._defaults()
        self._footer()


def build(stage_id, window):
    return MapBody(window)
