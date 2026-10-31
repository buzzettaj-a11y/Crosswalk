"""SetupsPanel (SPEC 10.3): save, check, load, delete, export and import set-ups. No client data is ever in one."""
from PySide6.QtWidgets import QFileDialog, QLineEdit, QWidget

from wholecount import copy
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import button, clear, hbox, label, vbox


class SetupsPanel(QWidget):
    def __init__(self, window, collapsed=True, parent=None):
        super().__init__(parent)
        self.window_ = window
        lay = vbox(self, spacing=8)
        head = hbox(spacing=8)
        head.addWidget(label(copy.get("setups.title"), role="row-title"), 1)
        self.toggle = button(copy.get("setups.show"), "quiet", "nav", name="setupsToggle")
        self.toggle.clicked.connect(self.flip)
        head.addWidget(self.toggle)
        lay.addLayout(head)
        lay.addWidget(label(copy.get("setups.no_client_data"), role="note", wrap=True))
        self.inner = QWidget()
        il = vbox(self.inner, spacing=8)
        row = hbox(spacing=8)
        self.name = QLineEdit()
        self.name.setPlaceholderText(copy.get("setups.name_placeholder"))
        self.note = QLineEdit()
        self.note.setPlaceholderText(copy.get("setups.note_placeholder"))
        self.save = HeldAction("setups.save", "secondary")
        self.save.clicked.connect(self.do_save)
        for w in (self.name, self.note):
            row.addWidget(w, 1)
            window.run_hold.register(w)
        row.addWidget(self.save)
        window.run_hold.register(self.save)
        il.addLayout(row)
        io = hbox(spacing=8)
        self.export_ = button(copy.get("setups.export"), "quiet", "nav", name="setupsExport")
        self.import_ = button(copy.get("setups.import"), "quiet", "nav", name="setupsImport")
        self.export_.clicked.connect(self.do_export)
        self.import_.clicked.connect(self.do_import)
        window.run_hold.register(self.import_)
        io.addWidget(self.export_)
        io.addWidget(self.import_)
        io.addStretch(1)
        il.addLayout(io)
        il.addWidget(label(copy.get("setups.export_note"), role="caption", wrap=True))
        self.list = vbox(spacing=6)
        il.addLayout(self.list)
        self.report = label("", role="note", wrap=True, name="setupsReport")
        il.addWidget(self.report)
        lay.addWidget(self.inner)
        self.inner.setVisible(not collapsed)
        self.refresh()

    def flip(self):
        self.inner.setVisible(not self.inner.isVisible())
        self.toggle.setText(copy.get("setups.hide" if self.inner.isVisible() else "setups.show"))

    def refresh(self):
        clear(self.list)
        for s in self.window_.bridge.saved_setups():
            row = QWidget()
            rl = hbox(row, spacing=8)
            rl.addWidget(label(copy.get("setups.row", name=s.name, files=", ".join(s.file_names) or "-"), role="note"), 1)
            for key, fn in (("setups.check", lambda _=False, s=s: self.do_check(s)),
                            ("setups.load", lambda _=False, s=s: self.do_load(s, False)),
                            ("setups.load_fitting", lambda _=False, s=s: self.do_load(s, True)),
                            ("setups.delete", lambda _=False, s=s: self.do_delete(s))):
                b = button(copy.get(key), "quiet", "nav" if key != "setups.delete" else "lesser")
                b.clicked.connect(fn)
                if key != "setups.check":
                    self.window_.run_hold.register(b)
                rl.addWidget(b)
            self.list.addWidget(row)

    def do_save(self):
        name = self.name.text().strip()
        if not name:
            self.report.setText(copy.get("setups.need_name"))
            return
        self.window_.bridge.save_setup(name, self.note.text().strip())
        self.report.setText(copy.get("setups.saved", name=name))
        self.refresh()

    def do_check(self, s):
        f = self.window_.bridge.setup_fit(s)
        self.report.setText(copy.get("setups.fit", fits=", ".join(f.fits) or "-", missing=", ".join(f.missing) or "-"))
        return f

    def do_load(self, s, only_fitting):
        if self.window_.run_hold.active:
            return
        self.window_.bridge.load_setup(s, only_fitting)

    def do_delete(self, s):
        if self.window_.run_hold.active:
            return
        if self.window_.confirm(copy.get("setups.delete_title"), (copy.get("setups.delete_confirm", name=s.name),),
                                copy.get("setups.delete"), copy.get("close.keep")):
            self.window_.bridge.delete_setup(s)
            self.refresh()

    def do_export(self):
        path, _ = QFileDialog.getSaveFileName(self, copy.get("setups.export"), "", copy.get("setups.filter"))
        if path:
            self.window_.bridge.export_setup(path)

    def do_import(self):
        path, _ = QFileDialog.getOpenFileName(self, copy.get("setups.import"), "", copy.get("setups.filter"))
        if path:
            self.window_.bridge.import_setup(path)
            self.refresh()
