"""Imports the whole app import graph without starting the UI. Used by the import-graph test and `python -m wholecount.dev check`."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy, pandas, openpyxl                      # noqa: E401,F401,E402
from lxml import etree                             # noqa: F401,E402
from PySide6 import QtCore, QtGui, QtWidgets       # noqa: F401,E402
import geosupport                                  # noqa: F401,E402
