"""Matching lines: the proposal and Likely lines, saved for this computer (M13 CAL-7), and the regression check (CAL-6)."""
from PySide6.QtWidgets import QSpinBox

from wholecount import copy
from wholecount.session import calibration as cs
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import button, hbox, label, set_prop
from wholecount.ui.widgets.tonetag import ToneTag


class LinesCard(Card):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("linesCard")
        self.body.addWidget(label(copy.get("settings.lines.title"), role="row-title"))
        self.boxes, self.current, self.suggested = {}, {}, {}
        for key in ("possible", "likely"):
            row = hbox(spacing=8)
            row.addWidget(label(copy.get(f"settings.lines.{key}"), role="note"), 1)
            box = QSpinBox()
            box.setObjectName(f"line_{key}")
            box.setRange(cs.settings()["possible_min_lowest"], 200)
            window.run_hold.register(box)
            self.boxes[key] = box
            self.current[key] = label("", role="caption", name=f"lineNow_{key}")
            row.addWidget(box)
            row.addWidget(self.current[key])
            if key == "possible":
                self.suggested[key] = label("", role="caption", name="lineSuggested")
                row.addWidget(self.suggested[key])
            self.body.addLayout(row)
        row = hbox(spacing=8)
        self.save_button = HeldAction("settings.lines.save", "primary")
        self.save_button.setObjectName("linesSave")
        self.save_button.clicked.connect(lambda: self.save())
        window.run_hold.register(self.save_button)
        self.check_button = button(copy.get("settings.lines.check"), "quiet", "nav", name="linesCheck")
        self.check_button.clicked.connect(lambda: self.check())
        row.addWidget(self.save_button)
        row.addWidget(self.check_button)
        row.addStretch(1)
        self.body.addLayout(row)
        self.message = label("", role="note", wrap=True, name="linesMessage")
        self.body.addWidget(self.message)
        self.regression = label("", role="caption", wrap=True, name="linesRegression")
        self.body.addWidget(self.regression)
        self.tag = ToneTag("", "neutral")
        self.tag.setObjectName("linesTag")
        self.tag.hide()
        self.body.addWidget(self.tag)
        self._loaded = False

    @property
    def session(self):
        return getattr(self.window_.bridge, "session", None)

    def save(self):
        s = self.session
        if s is None:
            return False
        try:
            cmd = cs.SetThresholds(self.boxes["possible"].value(), self.boxes["likely"].value())
        except cs.CalibrationRefused:
            self.message.setText(copy.get("settings.lines.refused", lo=cs.settings()["possible_min_lowest"]))
            return False
        cmd.run(s, self.window_.bridge.prefs_store)
        self.message.setText(copy.get("settings.lines.saved"))
        self.window_.refresh()
        return True

    def check(self):
        s = self.session
        bridge = self.window_.bridge
        reg = cs.run_regression(s, unprotect=bridge.dpapi[1] if bridge.dpapi else None) if s is not None else None
        if reg is None:
            self.regression.setText(copy.get("settings.lines.no_labels"))
            self.tag.hide()
            return None
        self.regression.setText(
            copy.get("settings.lines.caught", b1=reg.caught_before.num, b2=reg.caught_before.den, a1=reg.caught_after.num,
                     a2=reg.caught_after.den) + " " +
            copy.get("settings.lines.precision", b1=reg.precision_before.num, b2=reg.precision_before.den,
                     a1=reg.precision_after.num, a2=reg.precision_after.den))
        self.tag.setText(copy.get("settings.lines.dropped" if reg.dropped else "settings.lines.held"))
        set_prop(self.tag, "tag", "needs" if reg.dropped else "confirmed")
        self.tag.show()
        return reg

    def update_view(self, v):
        s = self.session
        if s is None:
            return
        possible, likely = cs.thresholds(s)
        self.current["possible"].setText(copy.get("settings.lines.current", n=possible))
        self.current["likely"].setText(copy.get("settings.lines.current", n=likely))
        sug = self.window_.bridge.ui.get("suggested_line")
        self.suggested["possible"].setText(copy.get("settings.lines.suggested", n=sug) if sug is not None
                                           else copy.get("settings.lines.no_suggestion"))
        if not self._loaded:
            self.boxes["possible"].setValue(possible)
            self.boxes["likely"].setValue(likely)
            self._loaded = True
