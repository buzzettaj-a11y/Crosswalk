"""Draws build/wholecount.ico, a 256 px brand mark (the top bar's blue square), with Qt (M14 section 2). Nothing is fetched."""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "wholecount.ico"
BLUE = "#2d6a9f"


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    img = QImage(256, 256, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.fillRect(32, 32, 192, 192, QColor(BLUE))
    p.end()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ok = img.save(str(OUT), "ICO")
    del app
    print(OUT.relative_to(ROOT).as_posix() if ok else "icon not written")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
