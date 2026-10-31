"""The Download body."""
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QFrame, QWidget

from wholecount import copy
from wholecount.session.commands import SetupChange
from wholecount.session.frame import existing_names, folder_warning, receipt_text
from wholecount.session.pages import export_plan
from wholecount.ui.frame.stage_head import StageHead
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.confidence import ConfidenceBlock
from wholecount.ui.widgets.held import HeldAction, HoldReason
from wholecount.ui.widgets.setups import SetupsPanel
from wholecount.ui.widgets.style import button, clear, hbox, label, narrow_combo, set_prop, vbox
from wholecount.ui.widgets.tag import tag

FORMATS = ("csv", "xlsx", "json")
CLEAN = "Final_Clean_Mapped"
GATE_HOLDS = {"stale": "results.hold_stale", "balance_failed": "export.hold.balance", "low_confidence_unacked": "hold.low"}


class ExportBody(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        v = window.view
        lay = vbox(self, spacing=16)
        self.download = HeldAction("export.download", "primary", {"n": 0})
        self.download.setObjectName("downloadFiles")
        self.download.clicked.connect(self.start)
        window.run_hold.register(self.download)
        self.head = StageHead("export", [self.download], saved_progress=v.saved_progress, data_notes=v.data_notes)
        lay.addWidget(self.head)
        self.body = vbox(spacing=14)
        lay.addLayout(self.body)
        self.receipt_box = vbox(spacing=8)
        lay.addLayout(self.receipt_box)
        self.footer = label("", role="note", name="exportFooter", wrap=True)
        lay.addWidget(self.footer)
        lay.addStretch(1)
        self.columns_open = False
        self.receipt = None
        self.receipt_version = None
        self.cancelled_written = None
        self.failure = None
        self.update_view(v)

    @property
    def session(self):
        return self.window_.bridge.session

    def settings(self):
        return self.window_.bridge.export_settings()

    def set_setting(self, key, value):
        self.window_.bridge.dispatch(SetupChange("export_settings", key, value))

    # Holds

    def holds(self, plan):
        s = self.session
        if s is None or s.results is None:
            return [HoldReason("results.hold_stale")]
        gate = s.download_gate()
        out = [HoldReason(GATE_HOLDS[r]) for r in gate.reasons if r in GATE_HOLDS]
        if plan is not None and not plan.columns_on:
            out.append(HoldReason("export.hold.columns"))
        return out

    # Drawing

    def update_view(self, v):
        self.head.dataline.update_view(v.saved_progress, v.data_notes)
        clear(self.body)
        s = self.session
        plan = None
        if s is not None and s.results is not None and not s.stale:
            plan = export_plan(s, self.settings())
        self.download.set_holds(self.holds(plan))
        n = len(plan.files) if plan else 0
        self.download.set_label("export.download", n=n)
        if plan is None:
            self.body.addWidget(label(copy.get("results.hold_stale"), role="note", tone="amber", wrap=True))
            self.footer.setText(copy.get("export.footer.before"))
            return
        self._band(plan)
        if v.confidence is not None and v.confidence.level == "low":
            c = Callout("wrong")
            c.setObjectName("exportLow")
            c.body.addWidget(ConfidenceBlock(v, full=True, on_tick=self.window_.acknowledge_low))
            self.body.addWidget(c)
        self._formats()
        self._files(plan, v)
        self._columns(plan)
        sp = SetupsPanel(self.window_)
        sp.setObjectName("exportSetups")
        self.body.addWidget(sp)
        self._receipt()
        self.footer.setText(copy.get("export.footer.after" if self.receipt is not None else "export.footer.before"))

    def _band(self, plan):
        b = plan.balance
        f = QFrame()
        f.setObjectName("grayRow")
        fl = vbox(f, (14, 10, 14, 10))
        fl.addWidget(label(copy.get("export.band", counted=b["counted"], not_counted_yet=b["not_counted_yet"],
                                    aside=b["set_aside"], received=b["received"]), role="note", wrap=True,
                           name="exportBand"))
        self.body.addWidget(f)

    def _formats(self):
        row = hbox(spacing=0)
        row.addWidget(label(copy.get("export.format_label"), role="row-title"))
        row.addSpacing(10)
        for fmt in FORMATS:
            b = button(copy.get(f"export.format.all_{fmt}"), "segment", name=f"allFormat_{fmt}")
            b.clicked.connect(lambda _=False, f=fmt: self.set_all(f))
            self.window_.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        self.body.addLayout(row)

    def set_all(self, fmt):
        from wholecount.session.frame import data_file_ids

        self.set_setting("formats", {fid: fmt for fid in data_file_ids()})

    def set_format(self, fid, fmt):
        formats = dict(self.settings().formats)
        formats[fid] = fmt
        self.set_setting("formats", formats)

    def _files(self, plan, v):
        st = self.settings()
        practice = self.session.results.practice
        for f in plan.files:
            fid = f.file_id.value
            card = QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(64)
            cl = hbox(card, (14, 8, 14, 8), 12)
            left = vbox(spacing=2)
            left.addWidget(label(f.name, role="row-title", name=f"fileName_{fid}"))
            left.addWidget(label(copy.get(f"export.file.{fid.lower()}"), role="note", wrap=True))
            left.addWidget(label(copy.get("export.file.size", rows=f.rows, cols=f.cols), role="caption",
                                 name=f"fileSize_{fid}"))
            if fid == CLEAN:
                box = QCheckBox(copy.get("export.coords_box"))
                box.setObjectName("exactCoordinates")
                box.setChecked(st.exact_coordinates)
                box.toggled.connect(lambda on: self.set_setting("exact_coordinates", on))
                self.window_.run_hold.register(box)
                left.addWidget(box)
                if st.exact_coordinates:
                    left.addWidget(label(copy.get("export.coords.note"), role="note", tone="amber", wrap=True,
                                         name="coordsNote"))
            cl.addLayout(left, 1)
            if f.fixed_format:
                cl.addWidget(tag(copy.get("export.fixed", fmt=f.fmt.upper()), "neutral"), 0, Qt.AlignVCenter)
            else:
                sel = QComboBox()
                narrow_combo(sel, 6)
                sel.setObjectName(f"format_{fid}")
                for fmt in FORMATS:
                    sel.addItem(copy.get(f"export.format.{fmt}"), fmt)
                sel.setCurrentIndex(max(0, sel.findData(f.fmt)))
                sel.activated.connect(lambda _, sel=sel, fid=fid: self.set_format(fid, sel.currentData()))
                self.window_.run_hold.register(sel)
                cl.addWidget(sel, 0, Qt.AlignVCenter)
            if fid == "Map_Points":
                left.addWidget(self._map_points_box(st.map_points, practice))
            else:
                cl.addWidget(tag(copy.get("export.always"), "neutral"), 0, Qt.AlignVCenter)
            self.body.addWidget(card)
        if practice:
            self.body.addWidget(label(copy.get("outputs.practice.no_maps"), role="note", tone="amber", wrap=True,
                                      name="practiceNoMaps"))
        if practice or not st.map_points:
            # Map_Points isn't in the plan while it's off (or in a practice run), so its switch gets a card of its own.
            card = Card()
            card.body.addWidget(label(copy.get("export.file.map_points"), role="note", wrap=True))
            card.body.addWidget(self._map_points_box(st.map_points and not practice, practice))
            self.body.addWidget(card)

    def _map_points_box(self, on, practice):
        """Write Map_Points, off by default. In a practice run it's held, and the practice sentence says why (SPEC 9.1)."""
        box = QCheckBox(copy.get("export.map_points"))
        box.setObjectName("writeMapPoints")
        box.setChecked(on)
        if practice:
            box.setEnabled(False)
            box.setAccessibleDescription(copy.get("outputs.practice.no_maps"))
        else:
            box.toggled.connect(lambda v: self.set_setting("map_points", v))
            self.window_.run_hold.register(box)
        return box

    def _columns(self, plan):
        card = Card()
        card.setObjectName("columnsCard")
        top = hbox(spacing=8)
        top.addWidget(label(copy.get("export.columns.title"), role="row-title"))
        top.addWidget(label(copy.get("export.columns.count", n=len(plan.columns_on), m=len(plan.columns)), role="caption",
                            name="columnsCount"), 1)
        for key in ("all", "none", "reset"):
            b = button(copy.get(f"export.columns.{key}"), "quiet", "nav", name=f"columns_{key}")
            b.clicked.connect(lambda _=False, k=key: self.columns_bulk(k, plan))
            self.window_.run_hold.register(b)
            top.addWidget(b)
        show = button(copy.get("setups.hide" if self.columns_open else "setups.show"), "quiet", "nav", name="columnsToggle")
        show.clicked.connect(self._toggle_columns)
        top.addWidget(show)
        card.body.addLayout(top)
        if self.columns_open:
            from PySide6.QtWidgets import QGridLayout

            grid = QGridLayout()
            on = set(plan.columns_on)
            for i, col in enumerate(plan.columns):
                chip = button(col, "chip", name=f"chip_{col}")
                set_prop(chip, "selected", col in on)
                chip.clicked.connect(lambda _=False, c=col: self.toggle_column(c, plan))
                self.window_.run_hold.register(chip)
                grid.addWidget(chip, i // 6, i % 6)
            card.body.addLayout(grid)
        self.body.addWidget(card)

    def _toggle_columns(self):
        self.columns_open = not self.columns_open
        self.update_view(self.window_.view)

    def _off(self):
        from wholecount.session.frame import clean_file_id

        stored = dict(self.session.setup.get("export_settings", "columns_off", {}) or {})
        return clean_file_id(), {k: frozenset(v) for k, v in stored.items()}

    def toggle_column(self, col, plan):
        fid, off = self._off()
        cur = set(off.get(fid, frozenset()))
        cur ^= {col}
        off[fid] = tuple(sorted(cur))
        self.set_setting("columns_off", off)

    def columns_bulk(self, how, plan):
        fid, off = self._off()
        off[fid] = tuple(sorted(plan.columns)) if how == "none" else ()
        self.set_setting("columns_off", off)

    # Download

    def start(self, folder=None):
        if self.download.held:
            return False
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, copy.get("export.folder"))
            if not folder:
                return False
        folder = pathlib.Path(folder)
        kind = folder_warning(folder)
        if kind and not self.window_.confirm(copy.get("export.synced.title"), (copy.get("outputs.folder_callout"),),
                                             copy.get("export.synced.use"), copy.get("export.synced.other")):
            return False
        clash = existing_names(self.session, folder, self.settings())
        if clash and not self.window_.confirm(copy.get("export.replace.title"),
                                              (copy.get("export.replace.q", n=len(clash)), ", ".join(clash)),
                                              copy.get("export.replace.ok"), copy.get("review.cancel")):
            return False
        from wholecount.ui.jobs.actions import DownloadJob

        def done(kind, value):
            self.failure = value if kind == "failed" else None
            if kind == "done":
                self.receipt = value
                self.receipt_version = self.session.results.version
                self.window_.bridge.ui["downloaded"] = True
        return self.window_.start_job(DownloadJob(self.session, folder, self.settings(), done))

    def _receipt(self):
        clear(self.receipt_box)
        if self.failure:
            c = Callout("wrong")
            c.setObjectName("writeFailed")
            c.body.addWidget(label(copy.get(f"export.write.{self.failure}"), role="note", tone="amber", name="writeReason"))
            self.receipt_box.addWidget(c)
        if self.receipt is None:
            return
        c = Callout("decided")
        c.setObjectName("receipt")
        c.body.addWidget(label(copy.get("export.receipt.title"), role="h3"))
        from PySide6.QtWidgets import QGridLayout

        grid = QGridLayout()
        for i, k in enumerate(("file", "path", "rows", "cols", "time")):
            grid.addWidget(label(copy.get(f"export.receipt.col.{k}"), role="column-head"), 0, i)
        for r, f in enumerate(self.receipt.files, start=1):
            p = pathlib.Path(f.path)
            for i, text in enumerate((p.name, str(p), f"{f.rows:,}", f"{f.columns:,}", f.time_iso)):
                grid.addWidget(label(text, role="caption", wrap=i == 1), r, i)
        grid.setColumnStretch(1, 1)
        c.body.addLayout(grid)
        c.body.addWidget(label(copy.get("export.receipt.nothing"), role="note", name="receiptNothing"))
        for key, params in self.receipt.notes:
            c.body.addWidget(label(copy.get(key, **params), role="note", wrap=True))
        if self.receipt_version != self.session.results.version:
            c.body.addWidget(label(copy.get("export.receipt.changed"), role="note", tone="amber"))
        row = hbox(spacing=8)
        cp = button(copy.get("export.receipt.copy"), "secondary", name="copyReceipt")
        cp.clicked.connect(self.copy_receipt)
        again = button(copy.get("export.receipt.again"), "quiet", "nav", name="downloadAgain")
        again.clicked.connect(lambda: self.start())
        self.window_.run_hold.register(again)
        row.addWidget(cp)
        row.addWidget(again)
        row.addStretch(1)
        c.body.addLayout(row)
        self.receipt_box.addWidget(c)

    def copy_receipt(self):
        from PySide6.QtGui import QGuiApplication

        text = receipt_text(self.receipt)
        QGuiApplication.clipboard().setText(text)
        return text


def build(stage_id, window):
    return ExportBody(window)
