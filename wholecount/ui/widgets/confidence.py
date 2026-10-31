"""ConfidenceBlock: one widget for the ledger, the popover and, from M12, the Process callout (SPEC 7.4, 11.7).

The level and the reason sentence are the engine's. The thresholds in the popover come from settings/confidence.toml
through FrameView. Never green for confidence. The only blue is the tick box and links.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QWidget

from wholecount import copy
from wholecount.session.frame import confidence_reason
from wholecount.ui.widgets.style import button, hbox, label, set_prop, vbox

MISSES = {"counted": ("counted_short",), "open_pairs": ("pairs_open",),
          "placed": ("placed_short", "placed_unavailable_no_geocoder", "placed_unavailable_none_looked_up")}


def level_word(conf):
    return copy.get(f"confidence.level.{conf.level}")


def measure_rows(conf):
    """(name text, value text, need text, misses High) for each of the three measures."""
    th = conf.thresholds
    codes = {code for code, _ in conf.parts}
    out = []
    for name, num, den in conf.measures:
        if num is None:
            value = copy.get("ledger.conf.value.unavailable")
        elif den is None:
            value = copy.get("ledger.conf.value.count", num=num)
        else:
            value = copy.get("ledger.conf.value.fraction", num=num, den=den)
        if name == "open_pairs":
            need = copy.get("ledger.conf.need.pairs", high=th.get("high_open_pairs", 0))
        else:
            high = th.get("high_counted_pct" if name == "counted" else "high_placed_pct", 0)
            need = copy.get("ledger.conf.need.pct", high=high, low=th.get("low_pct", 0))
        out.append((copy.get(f"ledger.conf.measure.{name}"), value, need, bool(codes & set(MISSES.get(name, ())))))
    return out


class TickBox(QFrame):
    def __init__(self, on_tick, parent=None):
        super().__init__(parent)
        self.setObjectName("tickBox")
        lay = hbox(self, (10, 8, 10, 8), 8)
        self.check = QCheckBox()
        self.check.setAccessibleName(copy.get("ledger.conf.tick"))
        self.text = label(copy.get("ledger.conf.tick"), role="note", tone="blue", wrap=True)
        lay.addWidget(self.check, 0, Qt.AlignTop)
        lay.addWidget(self.text, 1)
        self.check.toggled.connect(lambda on: on and on_tick())


class ConfidencePopover(QFrame):
    def __init__(self, conf, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("popover")
        self.setFixedWidth(360)
        lay = vbox(self, (16, 14, 16, 14), 10)
        lay.addWidget(label(copy.get("ledger.kicker.confidence"), role="kicker"))
        self.rows = []
        for name, value, need, miss in measure_rows(conf):
            box = vbox(spacing=2)
            top = hbox(spacing=8)
            top.addWidget(label(name, role="row-title"), 1)
            v = label(value, role="row-title", tone="amber" if miss else "ink")
            top.addWidget(v)
            box.addLayout(top)
            n = label(need, role="caption", wrap=True)
            box.addWidget(n)
            lay.addLayout(box)
            self.rows.append((name, v, n))
        self.calibration = None
        if conf.calibration is not None:
            date, rates = conf.calibration
            self.calibration = label(copy.get("ledger.conf.calibration", date=date, rates=rates), role="caption", wrap=True)
            lay.addWidget(self.calibration)


class ConfidenceBlock(QWidget):
    def __init__(self, view, full=True, on_tick=None, parent=None):
        super().__init__(parent)
        self.on_tick = on_tick or (lambda: None)
        self.lay = vbox(self, spacing=6)
        self.popover = None
        self.tick = None
        self.update_view(view, full)

    def update_view(self, view, full=True):
        from wholecount.ui.widgets.style import clear

        clear(self.lay)
        self.tick = None
        self.level = self.reason = None
        conf = view.confidence
        if conf is None or conf.level is None:
            self.lay.addWidget(label(copy.get("ledger.conf.before"), role="note", wrap=True, name="confBefore"))
            return
        self.conf = conf
        self.level = label(level_word(conf), role="level", tone="ink" if conf.level == "high" else "amber", name="confLevel")
        self.lay.addWidget(self.level)
        self.reason = label(confidence_reason(conf), role="note", tone="ink-2", wrap=True, name="confReason")
        self.lay.addWidget(self.reason)
        self.how = button(copy.get("ledger.conf.how"), "quiet", "nav")
        self.how.clicked.connect(self.open_popover)
        self.lay.addWidget(self.how, 0, Qt.AlignLeft)
        if full and conf.level == "low":
            self.tick = TickBox(self.on_tick)
            self.tick.check.blockSignals(True)
            self.tick.check.setChecked(conf.acknowledged)
            self.tick.check.blockSignals(False)
            self.lay.addWidget(self.tick)

    def open_popover(self):
        self.popover = ConfidencePopover(self.conf, self)
        self.popover.move(self.how.mapToGlobal(self.how.rect().bottomLeft()))
        self.popover.show()
        return self.popover

    def headline(self):
        return f"{self.level.text()}. {self.reason.text()}" if self.level else ""
