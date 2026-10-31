"""The crash message box (M14 section 3, A-15). M09's errors.install_excepthook stays the only sys.excepthook; this adds one
handler to it. The box says the program stopped, shows the error code (the exception's type and where it was raised, never
its message) and has a Copy the error code button. Nothing is logged to disk (H9)."""
from wholecount import copy, errors


def message(code):
    return copy.get("crash.message", code=code)


def show(exc, box_factory=None):
    """Shows the box. box_factory(text, code) is injected by tests so nothing blocks."""
    from wholecount.ui.jobs.runner import error_code

    code = error_code(exc)
    (box_factory or _qt_box)(message(code), code)
    return code


def _qt_box(text, code):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox

    if QApplication.instance() is None:
        return
    box = QMessageBox(QMessageBox.Critical, copy.get("crash.title"), text)
    copy_button = box.addButton(copy.get("crash.copy"), QMessageBox.ActionRole)
    box.addButton(copy.get("crash.close"), QMessageBox.AcceptRole)
    box.exec()
    if box.clickedButton() is copy_button:
        QGuiApplication.clipboard().setText(code)


def install(box_factory=None):
    errors.install_excepthook()
    errors.add_handler(lambda exc: show(exc, box_factory))
