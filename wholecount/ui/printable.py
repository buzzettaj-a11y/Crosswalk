"""The printable page (SPEC 9.3): M09's SummaryDoc drawn as plain HTML into a Qt document, and saved as PDF or a web page.
No external resource, no script and no link. There's no Print button, because a printer can be a network device (H1)."""
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument


def document(html):
    doc = QTextDocument()
    doc.setHtml(html)
    return doc


def save_pdf(html, path):
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setResolution(96)
    doc = document(html)
    doc.setPageSize(writer.pageLayout().paintRectPixels(96).size().toSizeF())
    doc.print_(writer)
    return path
