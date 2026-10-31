"""confirm(): a modal 440px dialog with a title, one paragraph and two buttons (M12 section 0). Every use is a copy ID, so
the wording lint covers it. The default focus is the cancel button for anything that discards or accepts in bulk."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from wholecount import copy
from wholecount.ui.widgets.style import button, hbox, label, vbox

WIDTH = 440
HOOK = None                               # tests set this to answer without a dialog: fn(copy_id, params) -> bool


class ConfirmDialog(QDialog):
    def __init__(self, parent, copy_id, params, ok_label, cancel_label, safe_default=True):
        super().__init__(parent)
        self.setModal(True)
        self.setFixedWidth(WIDTH)
        title_key = f"{copy_id}_title"
        lay = vbox(self, (24, 20, 24, 20), 12)
        try:
            lay.addWidget(label(copy.get(title_key), role="h3", wrap=True))
        except KeyError:
            pass
        lay.addWidget(label(copy.get(copy_id, **params), role="body", wrap=True, name="confirmText"))
        row = hbox(spacing=8)
        row.addStretch(1)
        self.cancel = button(copy.get(cancel_label), "secondary", name="confirmCancel")
        self.ok = button(copy.get(ok_label), "primary", name="confirmOk")
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.accept)
        row.addWidget(self.cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)
        (self.cancel if safe_default else self.ok).setFocus(Qt.OtherFocusReason)
        (self.cancel if safe_default else self.ok).setDefault(True)


def confirm(parent, copy_id, params=None, ok_label="common.ok", cancel_label="close.keep", safe_default=True):
    if HOOK is not None:
        return HOOK(copy_id, dict(params or {}))
    return ConfirmDialog(parent, copy_id, dict(params or {}), ok_label, cancel_label, safe_default).exec() == QDialog.Accepted
