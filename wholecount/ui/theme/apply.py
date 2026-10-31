"""apply_theme(app): load the bundled fonts, set Archivo at a 13px pixel size, and apply the QSS (SPEC 11.2)."""
from functools import lru_cache

from wholecount.ui.theme import resource_path, tokens
from wholecount.ui.theme.build_qss import build_qss

FONT_FILES = ("Archivo-Regular.ttf", "Archivo-SemiBold.ttf", "Archivo-ExtraBold.ttf")
FAMILIES = ("Archivo", "Segoe UI", "sans-serif")
RUN_LOG = []          # in memory only (H9): font load failures, file names of bundled fonts only
FONT_STATUS = {}


@lru_cache(maxsize=1)
def qss():
    return build_qss(tokens())


def load_fonts():
    from PySide6.QtGui import QFontDatabase

    for name in FONT_FILES:
        fid = QFontDatabase.addApplicationFont(str(resource_path("fonts", name)))
        FONT_STATUS[name] = fid >= 0
        if fid < 0:
            RUN_LOG.append(("font_failed", name))
    return all(FONT_STATUS.values())


def apply_theme(app):
    from PySide6.QtGui import QFont

    ok = load_fonts()
    f = QFont()
    f.setFamilies(list(FAMILIES) if ok else ["Segoe UI", "sans-serif"])
    f.setPixelSize(13)
    app.setFont(f)
    app.setStyleSheet(qss())
    return ok
