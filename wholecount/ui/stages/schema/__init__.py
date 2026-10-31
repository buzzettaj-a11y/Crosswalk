"""Your columns (SPEC 4.1, 11.5): the fields every file is matched to, custom fields, and what each test does."""
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLineEdit, QSpinBox, QWidget

from wholecount import copy
from wholecount.session.commands import SetupChange
from wholecount.session.schema_edit import FieldType, SchemaError, check_default
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.steplist import Bar
from wholecount.ui.widgets.style import narrow_combo, button, clear, hbox, label, vbox

TYPES = (FieldType.TEXT, FieldType.WHOLE_NUMBER, FieldType.DECIMAL, FieldType.DATE, FieldType.YES_NO)
KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def type_text(t):
    return copy.get(f"schema.ftype.{'plain' if t.value == 'text' else t.value}")


def name_problem(schema, name):
    """The copy ID of what's wrong with a new field name, or None."""
    if not name:
        return None
    if not KEY_RE.fullmatch(name):
        return "schema.add.bad_name"
    if any(f.key.lower() == name.lower() for f in schema.fields):
        return "schema.add.taken"
    return None


class SchemaBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        go = button(copy.get("schema.continue"), "primary", name="continuePrepare")
        go.clicked.connect(lambda: window.go_to("prepare"))
        self.head = StageHead("schema", [go], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        cols = hbox(spacing=16)
        left = vbox(spacing=16)
        right = vbox(spacing=16)
        self.fields_card = Card()
        self.fields_card.setObjectName("fieldsCard")
        left.addWidget(self.fields_card)
        left.addWidget(self._add_card())
        left.addStretch(1)
        right.addWidget(self._rules_card())
        self.fit_card = Card()
        self.fit_card.setObjectName("fitCard")
        right.addWidget(self.fit_card)
        right.addStretch(1)
        cols.addLayout(left, 3)
        cols.addLayout(right, 2)
        lay.addLayout(cols)
        lay.addStretch(1)
        self.update_view(v)

    def schema(self):
        s = self.window_.bridge.session
        return s.schema() if s is not None else None

    def set_schema(self, new):
        self.window_.bridge.dispatch(SetupChange("schema", "schema", new))

    # Fields

    def _fields(self):
        c = self.fields_card
        clear(c.body)
        c.body.addWidget(label(copy.get("schema.fields.title"), role="row-title"))
        schema = self.schema()
        if schema is None:
            return
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        for i, k in enumerate(("#", "field", "handling", "type", "longest", "default", "required", "")):
            grid.addWidget(label(copy.get(f"schema.col.{k}") if k not in ("#", "") else k, role="column-head"), 0, i)
        for r, f in enumerate(schema.fields, start=1):
            grid.addWidget(label(str(r), role="caption"), r, 0)
            if f.builtin:
                grid.addWidget(label(f.key, role="row-title"), r, 1)
                grid.addWidget(label(copy.get(f"schema.handling.{f.key.lower()}"), role="caption", wrap=True), r, 2)
                grid.addWidget(label(type_text(f.type), role="caption"), r, 3)
                grid.addWidget(label(str(f.max_length or copy.get("schema.any")), role="caption"), r, 4)
                grid.addWidget(label(copy.get("schema.client_id_default") if f.key == "Client_ID" else (f.default or ""),
                                     role="caption", wrap=True), r, 5)
                if f.key == "Client_ID":
                    box = QCheckBox()
                    box.setObjectName("clientIdRequired")
                    box.setAccessibleName(copy.get("schema.required_client_id"))
                    box.setChecked(f.required)
                    box.toggled.connect(lambda on: self.set_schema(self.schema().with_required("Client_ID", on)))
                    self.window_.run_hold.register(box)
                    grid.addWidget(box, r, 6)
                else:
                    grid.addWidget(label(copy.get("schema.required_mark") if f.required else "", role="caption"), r, 6)
            else:
                self._custom_row(grid, r, f)
        c.body.addLayout(grid)

    def _custom_row(self, grid, r, f):
        hold = self.window_.run_hold.register
        name = QLineEdit(f.key)
        name.setObjectName(f"custom_name_{f.key}")
        typ = QComboBox()
        narrow_combo(typ)
        for t in TYPES:
            typ.addItem(type_text(t), t)
        typ.setCurrentIndex(TYPES.index(f.type))
        longest = QSpinBox()
        longest.setRange(0, 1000)
        longest.setValue(f.max_length or 0)
        default = QLineEdit(f.default or "")
        req = QCheckBox()
        req.setChecked(f.required)
        req.setAccessibleName(copy.get("schema.required_for", name=f.key))
        rm = button(copy.get("schema.remove"), "quiet", "lesser", name=f"remove_{f.key}")
        for w in (name, typ, longest, default, req, rm):
            hold(w)

        def commit(*_):
            if self.window_.run_hold.active:
                return
            new_name = name.text().strip()
            schema = self.schema().remove_custom(f.key)
            if name_problem(schema, new_name):
                name.setText(f.key)
                return
            fresh = schema.add_custom(new_name, typ.currentData(), default.text() or None, longest.value() or None,
                                      req.isChecked())
            if fresh != self.schema():
                self.set_schema(fresh)
        name.editingFinished.connect(commit)
        default.editingFinished.connect(commit)
        longest.editingFinished.connect(commit)
        typ.activated.connect(commit)
        req.toggled.connect(commit)
        rm.clicked.connect(lambda: self.remove(f.key))
        grid.addWidget(name, r, 1)
        grid.addWidget(label(copy.get("schema.handling.custom"), role="caption", wrap=True), r, 2)
        for i, w in enumerate((typ, longest, default, req, rm), start=3):
            grid.addWidget(w, r, i)

    def remove(self, key):
        w = self.window_
        sv = w.bridge.survey()
        n = sum(1 for wk in (sv.works.values() if sv else ()) if wk.mapping.column_for(key) is not None)
        if n and not w.confirm(copy.get("schema.remove_title"), (copy.get("schema.remove_mapped", n=n),),
                               copy.get("schema.remove"), copy.get("close.keep")):
            return
        self.set_schema(self.schema().remove_custom(key))

    # Add a field

    def _add_card(self):
        c = Card()
        c.setObjectName("addCard")
        c.body.addWidget(label(copy.get("schema.add.title"), role="row-title"))
        row = hbox(spacing=8)
        self.new_name = QLineEdit()
        self.new_name.setObjectName("newName")
        self.new_name.setPlaceholderText(copy.get("schema.add.name"))
        self.new_type = QComboBox()
        for t in TYPES:
            self.new_type.addItem(type_text(t), t)
        self.new_len = QSpinBox()
        self.new_len.setRange(0, 1000)
        self.new_default = QLineEdit()
        self.new_default.setPlaceholderText(copy.get("schema.add.default"))
        for w in (self.new_name, self.new_type, self.new_len, self.new_default):
            row.addWidget(w, 1 if isinstance(w, QLineEdit) else 0)
            self.window_.run_hold.register(w)
        c.body.addLayout(row)
        self.add_problem = label("", role="note", tone="amber", name="addProblem")
        c.body.addWidget(self.add_problem)
        btns = hbox(spacing=8)
        self.add_button = HeldAction("schema.add.button", "primary")
        self.add_button.setObjectName("addField")
        self.add_button.clicked.connect(self.add)
        self.window_.run_hold.register(self.add_button)
        reset = button(copy.get("schema.reset"), "quiet", "lesser", name="resetSchema")
        reset.clicked.connect(self.reset)
        self.window_.run_hold.register(reset)
        btns.addWidget(self.add_button)
        btns.addWidget(reset)
        btns.addStretch(1)
        c.body.addLayout(btns)
        for sig in (self.new_name.textChanged, self.new_default.textChanged):
            sig.connect(lambda *_: self._check_add())
        self.new_type.currentIndexChanged.connect(lambda *_: self._check_add())
        return c

    def _check_add(self):
        schema = self.schema()
        name = self.new_name.text().strip()
        problem = name_problem(schema, name) if schema else None
        if not problem and self.new_default.text():
            t = self.new_type.currentData()
            if not check_default(t, self.new_default.text()):
                problem = ("schema.add.bad_default", {"type": type_text(t).lower()})
        if isinstance(problem, tuple):
            self.add_problem.setText(copy.get(problem[0], **problem[1]))
        else:
            self.add_problem.setText(copy.get(problem) if problem else "")
        holds = [HoldReason("schema.add.need_name")] if not name else []
        if problem:
            holds.append(HoldReason(problem[0], problem[1]) if isinstance(problem, tuple) else HoldReason(problem))
        self.add_button.set_holds(holds)
        return not holds

    def add(self):
        if not self._check_add():
            return
        try:
            new = self.schema().add_custom(self.new_name.text().strip(), self.new_type.currentData(),
                                           self.new_default.text() or None, self.new_len.value() or None)
        except SchemaError:
            return
        self.new_name.clear()
        self.new_default.clear()
        self.set_schema(new)

    def reset(self):
        from wholecount.session.schema_edit import default_schema

        if self.window_.confirm(copy.get("schema.reset_title"), (copy.get("schema.reset_q"),), copy.get("schema.reset"),
                                copy.get("close.keep")):
            self.set_schema(default_schema())

    # Right column

    def _rules_card(self):
        c = Card()
        c.body.addWidget(label(copy.get("schema.rules.title"), role="row-title"))
        for k in ("type", "length", "required"):
            c.body.addWidget(label(copy.get(f"schema.rules.{k}"), role="note", wrap=True))
        return c

    def _fit(self, sv):
        c = self.fit_card
        clear(c.body)
        c.body.addWidget(label(copy.get("schema.fit.title"), role="row-title"))
        works = [w for w in (sv.works.values() if sv else ())]
        if not works:
            c.body.addWidget(label(copy.get("schema.fit.none"), role="note", wrap=True))
            return
        total = len(self.schema().enabled_fields())
        for wk in works:
            have = sum(1 for f in self.schema().enabled_fields() if wk.mapping.column_for(f.key) is not None)
            c.body.addWidget(label(f"{wk.file_name}" + (f" / {wk.table.sheet}" if wk.table.sheet else ""), role="note"))
            bar = Bar(4)
            bar.set_fraction(have / total if total else 0, done=have == total)
            c.body.addWidget(bar)
            c.body.addWidget(label(copy.get("schema.fit.line", have=have, total=total), role="caption"))

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        self._fields()
        self._fit(self.window_.bridge.survey())
        self._check_add()


def build(stage_id, window):
    return SchemaBody(window)
