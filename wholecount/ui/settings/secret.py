"""Install secret: back up and restore (SPEC 5.1, 11.6.2, M13 BAK-4). The passphrase boxes show nothing."""
from PySide6.QtWidgets import QDialog, QFileDialog, QLineEdit

from wholecount import copy
from wholecount.session.backup import BackupRefused, BackupSecret, RestoreSecret, passphrase_min
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import button, hbox, label, vbox


def _secret_box(name, placeholder):
    box = QLineEdit()
    box.setObjectName(name)
    box.setEchoMode(QLineEdit.Password)
    box.setPlaceholderText(placeholder)
    return box


class PassphraseDialog(QDialog):
    """Asks twice and shows nothing. save(path) checks the two entries, then hands a BackupSecret to the card."""

    def __init__(self, card):
        super().__init__(card.window_)
        self.card = card
        self.setModal(True)
        self.setFixedWidth(460)
        lay = vbox(self, (24, 20, 24, 20), 10)
        lay.addWidget(label(copy.get("settings.secret.pass_title"), role="h3"))
        lay.addWidget(label(copy.get("settings.secret.pass_body", n=passphrase_min()), role="note", wrap=True,
                            name="passBody"))
        self.first = _secret_box("passFirst", copy.get("settings.secret.pass_first"))
        self.again = _secret_box("passAgain", copy.get("settings.secret.pass_again"))
        lay.addWidget(self.first)
        lay.addWidget(self.again)
        self.refusal = label("", role="note", tone="amber", wrap=True, name="passRefusal")
        lay.addWidget(self.refusal)
        row = hbox(spacing=8)
        row.addStretch(1)
        cancel = button(copy.get("review.cancel"), "secondary", name="passCancel")
        cancel.clicked.connect(self.reject)
        self.ok = button(copy.get("settings.secret.save"), "primary", name="passSave")
        self.ok.clicked.connect(lambda: self.save())
        row.addWidget(cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)

    def save(self, path=None):
        try:
            BackupSecret(self.first.text(), self.again.text(), "x")
        except BackupRefused as e:
            params = {"n": passphrase_min()} if e.code == "passphrase_short" else {}
            self.refusal.setText(copy.get(f"settings.secret.refused.{e.code}", **params))
            return False
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, copy.get("settings.secret.choose_file"), "wholecount-secret.wcb",
                                                  copy.get("settings.secret.file_filter"))
            if not path:
                return False
        backup = BackupSecret(self.first.text(), self.again.text(), path)
        self.first.clear()
        self.again.clear()
        self.accept()
        return self.card.start_backup(backup)


class RestoreDialog(QDialog):
    def __init__(self, card, path=None):
        super().__init__(card.window_)
        self.card = card
        self.path = path
        self.setModal(True)
        self.setFixedWidth(460)
        lay = vbox(self, (24, 20, 24, 20), 10)
        lay.addWidget(label(copy.get("settings.secret.restore_title"), role="h3"))
        self.passphrase = _secret_box("restorePass", copy.get("settings.secret.pass_first"))
        lay.addWidget(self.passphrase)
        self.warn = label(copy.get("settings.secret.replace_warn"), role="note", tone="amber", wrap=True, name="replaceWarn")
        self.warn.hide()
        lay.addWidget(self.warn)
        self.word = QLineEdit()
        self.word.setObjectName("replaceWord")
        self.word.setPlaceholderText(copy.get("settings.secret.word"))
        self.word.hide()
        lay.addWidget(self.word)
        self.message = label("", role="note", wrap=True, name="restoreMessage")
        lay.addWidget(self.message)
        row = hbox(spacing=8)
        row.addStretch(1)
        cancel = button(copy.get("review.cancel"), "secondary", name="restoreCancel")
        cancel.clicked.connect(self.reject)
        self.ok = button(copy.get("settings.secret.restore_go"), "primary", name="restoreGo")
        self.ok.clicked.connect(lambda: self.restore())
        row.addWidget(cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)

    def restore(self):
        w = self.card.window_
        if self.path is None:
            p, _ = QFileDialog.getOpenFileName(self, copy.get("settings.secret.open_file"), "",
                                               copy.get("settings.secret.file_filter"))
            if not p:
                return None
            self.path = p
        cmd = RestoreSecret(self.path, self.passphrase.text(), self.word.text())
        try:
            res = cmd.run(w.bridge.session, w.bridge.secret_store)
        except BackupRefused as e:   # its code picks a fixed sentence, never the OS text
            self.message.setText(copy.get("settings.secret.not_backup" if e.code == "not_a_backup" else "settings.secret.wrong"))
            return "refused"
        if res.same:
            self.message.setText(copy.get("settings.secret.same"))
            return "same"
        if res.needs_word:
            self.warn.show()
            self.word.show()
            return "needs_word"
        self.passphrase.clear()
        self.message.setText(copy.get("settings.secret.restored"))
        w.refresh()
        return "restored"


class SecretCard(Card):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("secretCard")
        self.body.addWidget(label(copy.get("settings.secret.title"), role="row-title"))
        self.body.addWidget(label(copy.get("settings.secret.body"), role="note", wrap=True, name="secretBody"))
        row = hbox(spacing=8)
        self.backup_button = HeldAction("settings.secret.backup", "secondary")
        self.backup_button.setObjectName("secretBackup")
        self.backup_button.clicked.connect(lambda: self.backup())
        self.restore_button = HeldAction("settings.secret.restore", "secondary")
        self.restore_button.setObjectName("secretRestore")
        self.restore_button.clicked.connect(lambda: self.restore())
        for b in (self.backup_button, self.restore_button):
            window.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        self.body.addLayout(row)
        self.message = label("", role="note", wrap=True, name="secretMessage")
        self.body.addWidget(self.message)
        self.dialog = None

    def backup(self):
        self.dialog = PassphraseDialog(self)
        self.dialog.open()
        return self.dialog

    def start_backup(self, backup):
        from wholecount.ui.jobs.actions import BackupJob

        if backup.folder_warning() and not self.window_.confirm(copy.get("export.synced.title"),
                                                                (copy.get("outputs.folder_callout"),),
                                                                copy.get("export.synced.use"), copy.get("export.synced.other")):
            return False
        return self.window_.start_job(BackupJob(self.window_.bridge.session, backup,
                                                lambda n: self.message.setText(copy.get("settings.secret.saved", n=n))))

    def restore(self, path=None):
        self.dialog = RestoreDialog(self, path)
        self.dialog.open()
        return self.dialog

    def update_view(self, v):
        pass

