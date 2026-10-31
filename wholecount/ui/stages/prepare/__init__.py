"""Tidy up (SPEC 6.3, 11.5, boards C1b and C1c): add a step, then see every step grouped by rule, source or who added it.
Every step adds columns and removes nothing. A removed step never runs."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QLineEdit, QSpinBox, QWidget

from wholecount import copy
from wholecount.session.commands import ConfirmStage, SetupChange
from wholecount.session.steps_edit import restore_step, with_added, without_step
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card, pluralize, source_label
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.style import narrow_combo, button, clear, hbox, label, set_prop, vbox
from wholecount.ui.widgets.tag import tag

RULES = ("calc_zip", "clean", "split_delim", "split_address", "split_name")
CASES = (("none", "tidy.case.none"), ("title_name", "tidy.case.title"), ("upper", "tidy.case.upper"),
         ("lower", "tidy.case.lower"))
DELIMS = ("comma", "semicolon", "pipe", "tab", "space", "custom")
FORMS = (("auto", "tidy.form.last_first_m"), ("first_last", "tidy.form.first_m_last"), ("last_first", "tidy.form.last_first"))
GROUPINGS = ("rule", "source", "who")
CHIP_LIMIT = 10


def result_text(result, rows):
    """The dry-run sentence for a step: what it did, or, amber, what it failed to find (SPEC 6.3)."""
    if result is None:
        return copy.get("tidy.checking"), False
    if result.amber:
        return copy.get(f"tidy.amber.{result.amber_reason}") + " " + copy.get("tidy.amber.safe", rows=rows), True
    c = result.counts
    if "changed" in c:
        return copy.get("tidy.result.changed", n=c["changed"], rows=rows), False
    if "split" in c:
        return copy.get("tidy.result.split", n=c["split"], rows=rows), False
    return copy.get("tidy.result.zip", found=c.get("found", 0), kept=c.get("kept", 0),
                    missing=c.get("not_worked_out", 0)), False


def step_columns(step):
    p = step.params
    cols = p.get("columns") or [p.get("column") or p.get("street_col") or ""]
    return ", ".join(c for c in cols if c)


def form_holds(kind, source, values):
    """What a step still needs, each piece naming itself."""
    holds = []
    if not source:
        holds.append(HoldReason("tidy.hold.source"))
    need = {"calc_zip": "street_col", "clean": "columns", "split_delim": "column", "split_address": "column",
            "split_name": "column"}[kind]
    if not values.get(need):
        holds.append(HoldReason(f"tidy.hold.{need}"))
    if kind == "split_delim" and values.get("delimiter") == "custom" and not values.get("custom"):
        holds.append(HoldReason("tidy.hold.custom"))
    return holds


class PrepareBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        go = button(copy.get("tidy.continue"), "primary", name="continueMap")
        go.clicked.connect(self.continue_)
        self.head = StageHead("prepare", [go], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.rule = "clean"
        self.form_values = {}
        self.grouping = window.bridge.pref("tidy_group_by", "rule")
        lay.addWidget(self._add_card())
        self.list_card = vbox(spacing=10)
        lay.addLayout(self.list_card)
        lay.addStretch(1)
        self.update_view(v)

    def continue_(self):
        self.window_.bridge.dispatch(ConfirmStage("prepare"))
        self.window_.go_to("map")

    # Add a step

    def _add_card(self):
        c = Card()
        c.setObjectName("addStep")
        c.body.addWidget(label(copy.get("tidy.add.title"), role="h3"))
        c.body.addWidget(label(copy.get("tidy.add.note"), role="note"))
        row = hbox(spacing=10)
        self.rule_cards = {}
        for r in RULES:
            b = button("", "segment", name=f"rule_{r}")
            set_prop(b, "kind", "rulecard")
            inner = vbox(b, (12, 10, 12, 10), 4)
            t = label(copy.get(f"tidy.rule.{r}.name"), role="row-title", wrap=True)
            d = label(copy.get(f"tidy.rule.{r}.desc"), role="caption", wrap=True)
            for x in (t, d):
                x.setAttribute(Qt.WA_TransparentForMouseEvents)
                inner.addWidget(x)
            b.setMinimumHeight(110)
            b.setAccessibleName(copy.get(f"tidy.rule.{r}.name"))
            b.clicked.connect(lambda _=False, r=r: self.pick_rule(r))
            self.rule_cards[r] = b
            row.addWidget(b, 1)
        c.body.addLayout(row)
        self.form = vbox(spacing=8)
        c.body.addLayout(self.form)
        self.add_button = HeldAction("tidy.add.button", "primary")
        self.add_button.setObjectName("addStepButton")
        self.add_button.clicked.connect(self.add)
        self.window_.run_hold.register(self.add_button)
        c.body.addWidget(self.add_button, 0, Qt.AlignLeft)
        return c

    def pick_rule(self, r):
        self.rule = r
        self.form_values = {}
        self._form()

    def _sources(self):
        sv = self.window_.bridge.survey()
        return [(k, w) for k, w in (sv.works.items() if sv else ())]

    def _columns(self, key):
        sv = self.window_.bridge.survey()
        w = sv.work(key) if sv and key else None
        return list(w.prepared.names()) if w else []

    def _combo(self, name, items, value=None, optional=False):
        cb = QComboBox()
        narrow_combo(cb)
        cb.setObjectName(name)
        if optional:
            cb.addItem(copy.get("tidy.form.none"), "")
        for data, text in items:
            cb.addItem(text, data)
        if value is not None:
            cb.setCurrentIndex(max(0, cb.findData(value)))
        self.window_.run_hold.register(cb)
        return cb

    def _field(self, key, widget, note=None):
        box = vbox(spacing=2)
        box.addWidget(label(copy.get(f"tidy.form.{key}"), role="caption"))
        box.addWidget(widget)
        if note:
            box.addWidget(label(note, role="caption", wrap=True))
        self.form.addLayout(box)
        return widget

    def _form(self):
        for r, b in self.rule_cards.items():
            set_prop(b, "selected", r == self.rule)
        clear(self.form)
        v = self.form_values
        sources = self._sources()
        src = self._field("source", self._combo("formSource", [(k, w.file_name + (f" / {w.table.sheet}" if w.table.sheet
                                                                                 else "")) for k, w in sources],
                                                v.get("source"), optional=True))
        src.currentIndexChanged.connect(lambda *_: self._set("source", src.currentData(), redraw=True))
        cols = [(c, c) for c in self._columns(v.get("source"))]
        r = self.rule
        if r == "calc_zip":
            for key, opt in (("street_col", False), ("city_col", True), ("zip_col", True)):
                cb = self._field(key, self._combo(f"form_{key}", cols, v.get(key), optional=True))
                cb.currentIndexChanged.connect(lambda *_, k=key, cb=cb: self._set(k, cb.currentData()))
            mode = self._field("mode", self._combo("form_mode", [("blanks", copy.get("tidy.mode.blanks")),
                                                                 ("all", copy.get("tidy.mode.all"))], v.get("mode", "blanks")))
            mode.currentIndexChanged.connect(lambda *_: self._set("mode", mode.currentData()))
            name = self._field("new_name", self._edit("form_name", v.get("name", "Zip_calculated")))
            name.textChanged.connect(lambda t: self._set("name", t))
            backend = self.window_.bridge.backend_name()
            self.form.addWidget(label(copy.get("tidy.zip.backend.geosupport" if backend == "geosupport"
                                               else "tidy.zip.backend.reference"), role="note", wrap=True))
            self.form.addWidget(label(copy.get("tidy.zip.adds", name=v.get("name", "Zip_calculated")), role="note",
                                      wrap=True, name="zipAdds"))
        elif r == "clean":
            self._chips(cols)
            case = self._field("case", self._combo("form_case", [(k, copy.get(t)) for k, t in CASES], v.get("case", "none")))
            case.currentIndexChanged.connect(lambda *_: self._set("case", case.currentData()))
            for key in ("strip_junk", "strip_edge_punctuation"):
                box = QCheckBox(copy.get(f"tidy.form.{key}"))
                box.setObjectName(f"form_{key}")
                box.setChecked(bool(v.get(key)))
                box.toggled.connect(lambda on, k=key: self._set(k, on))
                self.window_.run_hold.register(box)
                self.form.addWidget(box)
        elif r == "split_delim":
            col = self._field("column", self._combo("form_column", cols, v.get("column"), optional=True))
            col.currentIndexChanged.connect(lambda *_: self._set("column", col.currentData()))
            d = self._field("delimiter", self._combo("form_delimiter", [(k, copy.get(f"tidy.delim.{k}")) for k in DELIMS],
                                                     v.get("delimiter", "comma")))
            d.currentIndexChanged.connect(lambda *_: self._set("delimiter", d.currentData(), redraw=True))
            if v.get("delimiter") == "custom":
                cu = self._field("custom", self._edit("form_custom", v.get("custom", "")))
                cu.textChanged.connect(lambda t: self._set("custom", t))
            ms = QSpinBox()
            ms.setObjectName("form_maxsplit")
            ms.setRange(0, 50)
            ms.setValue(v.get("maxsplit", 0))
            ms.valueChanged.connect(lambda n: self._set("maxsplit", n))
            self.window_.run_hold.register(ms)
            self._field("maxsplit", ms)
            c = v.get("column") or "column"
            names = self._field("names", self._edit("form_names", v.get("names_text", f"{c}_1, {c}_2")))
            names.textChanged.connect(lambda t: self._set("names_text", t))
        elif r == "split_address":
            col = self._field("column", self._combo("form_column", cols, v.get("column"), optional=True))
            col.currentIndexChanged.connect(lambda *_: self._set("column", col.currentData(), redraw=True))
            c = v.get("column") or "column"
            self.form.addWidget(label(copy.get("tidy.address.adds", prefix=f"{c}_"), role="note", wrap=True))
        elif r == "split_name":
            col = self._field("column", self._combo("form_column", cols, v.get("column"), optional=True))
            col.currentIndexChanged.connect(lambda *_: self._set("column", col.currentData(), redraw=True))
            f = self._field("form", self._combo("form_form", [(k, copy.get(t)) for k, t in FORMS], v.get("form", "auto")))
            f.currentIndexChanged.connect(lambda *_: self._set("form", f.currentData()))
            c = v.get("column") or "column"
            self.form.addWidget(label(copy.get("tidy.name.adds", prefix=f"{c}_"), role="note", wrap=True))
        self._holds()

    def _edit(self, name, text):
        e = QLineEdit(text)
        e.setObjectName(name)
        self.window_.run_hold.register(e)
        return e

    def _chips(self, cols):
        v = self.form_values
        picked = set(v.get("columns", ()))
        box = vbox(spacing=4)
        top = hbox(spacing=8)
        top.addWidget(label(copy.get("tidy.form.columns"), role="caption"))
        for key in ("all", "none", "invert"):
            b = button(copy.get(f"tidy.chips.{key}"), "quiet", "nav", name=f"chips_{key}")
            b.clicked.connect(lambda _=False, k=key: self._chip_all(k, [c for c, _ in cols]))
            top.addWidget(b)
        top.addWidget(label(copy.get("tidy.chips.count", n=len(picked), m=len(cols)), role="caption", name="chipCount"))
        top.addStretch(1)
        box.addLayout(top)
        row = hbox(spacing=6)
        shown = cols if v.get("chips_all") else cols[:CHIP_LIMIT]
        for c, _ in shown:
            chip = button(c, "chip", name=f"chip_{c}")
            set_prop(chip, "selected", c in picked)
            chip.clicked.connect(lambda _=False, c=c: self._chip(c))
            self.window_.run_hold.register(chip)
            row.addWidget(chip)
        if len(cols) > len(shown):
            more = button(copy.get("tidy.chips.more", n=len(cols) - len(shown)), "quiet", "nav", name="chipsMore")
            more.clicked.connect(lambda: self._set("chips_all", True, redraw=True))
            row.addWidget(more)
        row.addStretch(1)
        box.addLayout(row)
        self.form.addLayout(box)

    def _chip(self, c):
        cur = list(self.form_values.get("columns", ()))
        cur = [x for x in cur if x != c] if c in cur else cur + [c]
        self._set("columns", cur, redraw=True)

    def _chip_all(self, how, cols):
        cur = set(self.form_values.get("columns", ()))
        new = cols if how == "all" else [] if how == "none" else [c for c in cols if c not in cur]
        self._set("columns", new, redraw=True)

    def _set(self, key, value, redraw=False):
        self.form_values[key] = value
        if redraw:
            self._form()
        else:
            self._holds()

    def _holds(self):
        self.add_button.set_holds(form_holds(self.rule, self.form_values.get("source"), self.form_values))

    def params(self):
        v, r = self.form_values, self.rule
        if r == "calc_zip":
            p = {"street_col": v["street_col"], "mode": v.get("mode", "blanks"), "name": v.get("name") or "Zip_calculated"}
            for k in ("city_col", "zip_col"):
                if v.get(k):
                    p[k] = v[k]
            return p
        if r == "clean":
            return {"columns": list(v["columns"]), "case": v.get("case", "none"), "strip_junk": bool(v.get("strip_junk")),
                    "strip_edge_punctuation": bool(v.get("strip_edge_punctuation"))}
        if r == "split_delim":
            p = {"column": v["column"], "delimiter": v.get("delimiter", "comma"), "maxsplit": v.get("maxsplit", 0)}
            if p["delimiter"] == "custom":
                p["custom"] = v.get("custom", "")
                p["delimiter"] = "comma"
            names = [n.strip() for n in v.get("names_text", "").split(",") if n.strip()]
            if names:
                p["names"] = names
            return p
        if r == "split_address":
            return {"column": v["column"]}
        return {"column": v["column"], "form": v.get("form", "auto")}

    def add(self):
        if self.add_button.held:
            return
        key = self.form_values["source"]
        sv = self.window_.bridge.survey()
        t = sv.table(key)
        steps = with_added(sv.steps.get(key, ()), self.rule, self.params())
        self.window_.bridge.dispatch(SetupChange("steps", (t.file_name, t.idx), steps))

    # The list

    def _rows(self):
        sv = self.window_.bridge.survey()
        out = []
        for key, steps in (sv.steps.items() if sv else ()):
            w = sv.work(key)
            results = {r.step_id: r for r in w.prepared.results}
            for order, s in enumerate(steps):
                res = results.get(s.step_id)
                if s.removed:
                    res = self.window_.bridge.preview_step(key, s)
                out.append((key, w, order, s, res))
        return out

    def _list(self):
        clear(self.list_card)
        rows = self._rows()
        sv = self.window_.bridge.survey()
        sources = len(sv.works) if sv else 0
        head = hbox(spacing=10)
        head.addWidget(label(copy.get("tidy.list.title", n=len(rows), m=sources), role="row-title", name="stepsTitle"), 1)
        for g in GROUPINGS:
            b = button(copy.get(f"tidy.group.{g}"), "segment", name=f"group_{g}")
            set_prop(b, "selected", g == self.grouping)
            b.clicked.connect(lambda _=False, g=g: self.group_by(g))
            head.addWidget(b)
        self.list_card.addLayout(head)
        groups = {}
        order = []
        for row in rows:
            key, w, i, s, res = row
            g = {"rule": s.kind, "source": key,
                 "who": "removed" if s.removed else ("proposed" if s.origin == "proposed" else "added")}[self.grouping]
            if g not in groups:
                groups[g] = []
                order.append(g)
            groups[g].append(row)
        if self.grouping == "who":
            order = [g for g in ("proposed", "added", "removed") if g in groups]
        for g in order:
            self.list_card.addWidget(self._group(g, groups[g], sv))
        if self.grouping == "source" and sv:
            for key, w in sv.works.items():
                if key not in groups:
                    self.list_card.addWidget(label(copy.get("tidy.no_steps", name=w.file_name), role="note",
                                                   name="noSteps"))

    def group_by(self, g):
        self.grouping = g
        self.window_.bridge.set_pref("tidy_group_by", g)
        self._list()

    def _group(self, g, rows, sv):
        c = QFrame()
        c.setObjectName("card")
        lay = vbox(c)
        head = QFrame()
        head.setObjectName("groupHead")
        hl = vbox(head, (14, 10, 14, 10), 2)
        if self.grouping == "rule":
            hl.addWidget(label(copy.get(f"tidy.rule.{g}.name"), role="row-title"))
            n = len({r[0] for r in rows})
            hl.addWidget(label(pluralize("tidy.group.src", n) + " · " + copy.get(f"tidy.rule.{g}.desc"), role="caption",
                               wrap=True))
        elif self.grouping == "source":
            w = sv.work(g)
            hl.addWidget(source_label(w.table.letter, w.file_name))
            hl.addWidget(label(copy.get("tidy.group.in_order", n=len(rows)), role="caption"))
        else:
            hl.addWidget(label(copy.get(f"tidy.who.{g}"), role="row-title"))
        lay.addWidget(head)
        body = vbox(margins=(14, 8, 14, 8), spacing=6)
        for key, w, i, s, res in rows:
            body.addWidget(self._step_row(key, w, s, res))
        lay.addLayout(body)
        return c

    def _step_row(self, key, w, s, res):
        text, amber = result_text(res, len(w.table.rows))
        f = QFrame()
        f.setObjectName("amberRow" if amber and not s.removed else ("grayRow" if s.removed else "stepRow"))
        row = hbox(f, (10, 6, 10, 6), 10)
        left = vbox(spacing=2)
        top = hbox(spacing=8)
        if self.grouping != "source":
            top.addWidget(source_label(w.table.letter, w.file_name, role="note"))
        if self.grouping != "rule":
            top.addWidget(label(copy.get(f"tidy.rule.{s.kind}.name"), role="note"))
        top.addWidget(label(step_columns(s), role="note", tone="ink-2"))
        origin = "removed" if s.removed else s.origin
        top.addWidget(tag(copy.get(f"tidy.origin.{origin}"),
                          {"proposed": "neutral", "added": "confirmed", "removed": "neutral"}[origin]))
        top.addStretch(1)
        left.addLayout(top)
        left.addWidget(label(copy.get("tidy.removed") if s.removed else text, role="note",
                             tone="amber" if amber and not s.removed else "muted", wrap=True, name="stepResult"))
        row.addLayout(left, 1)
        t = self.window_.bridge.survey().table(key)
        if s.removed:
            b = button(copy.get("tidy.restore"), "quiet", "nav", name=f"restore_{s.step_id}")
            b.clicked.connect(lambda _=False, sid=s.step_id: self._edit_steps(key, t, restore_step, sid))
        else:
            b = button(copy.get("tidy.remove"), "quiet", "lesser", name=f"remove_{s.step_id}")
            b.clicked.connect(lambda _=False, sid=s.step_id: self._edit_steps(key, t, without_step, sid))
        b.setProperty("step_id", s.step_id)
        self.window_.run_hold.register(b)
        row.addWidget(b)
        f.step_id = s.step_id
        return f

    def _edit_steps(self, key, t, fn, sid):
        if self.window_.run_hold.active:
            return
        steps = fn(list(self.window_.bridge.survey().steps[key]), sid)
        self.window_.bridge.dispatch(SetupChange("steps", (t.file_name, t.idx), steps))

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        self._form()
        self._list()


def build(stage_id, window):
    return PrepareBody(window)
