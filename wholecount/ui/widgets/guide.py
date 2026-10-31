"""GuideDialog: the user guide in the app (M15 section 1). A contents list and a read-only QTextBrowser drawing what
build_guide() returns. Links only jump to anchors inside the guide; nothing opens outside the app."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QListWidget, QTextBrowser

from wholecount import copy
from wholecount.copy.guide import build_guide, to_html
from wholecount.ui.widgets.style import button, hbox, vbox


class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("guideDialog")
        self.guide = build_guide()
        self.setWindowTitle(self.guide.title)
        self.resize(920, 700)
        lay = vbox(self, (16, 16, 16, 16), 10)
        row = hbox(spacing=12)
        self.contents = QListWidget()
        self.contents.setObjectName("guideContents")
        self.contents.setFixedWidth(240)
        for i, s in enumerate(self.guide.sections, 1):
            self.contents.addItem(f"{i}. {s.title}")
        self.contents.currentRowChanged.connect(self.go)
        self.browser = QTextBrowser()
        self.browser.setObjectName("guideText")
        self.browser.setOpenLinks(False)       # openExternalLinks is off by default, and the offline scan forbids its setter
        self.browser.setHtml(to_html(self.guide))
        self.browser.anchorClicked.connect(lambda url: self.browser.scrollToAnchor(url.fragment()))
        row.addWidget(self.contents)
        row.addWidget(self.browser, 1)
        lay.addLayout(row, 1)
        close = button(copy.get("guide.close"), "secondary", name="guideClose")
        close.clicked.connect(self.reject)
        lay.addWidget(close, 0, Qt.AlignRight)

    def go(self, row):
        if 0 <= row < len(self.guide.sections):
            self.browser.scrollToAnchor(self.guide.sections[row].anchor)
