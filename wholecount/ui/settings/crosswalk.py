"""Saved crosswalk: off by default, turned on by a person, forgotten with a typed word (SPEC 10.5, M13 XW-1, XW-3)."""
from wholecount import copy
from wholecount.session import crosswalk as xw
from wholecount.ui.stages._common import Card
from wholecount.ui.widgets.held import HeldAction
from wholecount.ui.widgets.style import hbox, label
from wholecount.ui.widgets.tonetag import ToneTag


class CrosswalkCard(Card):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("crosswalkCard")
        top = hbox(spacing=8)
        top.addWidget(label(copy.get("settings.xw.title"), role="row-title"), 1)
        self.state_tag = ToneTag(copy.get("settings.xw.off"), "neutral")
        self.state_tag.setObjectName("crosswalkState")
        top.addWidget(self.state_tag)
        self.body.addLayout(top)
        self.body.addWidget(label(copy.get("settings.xw.body"), role="note", wrap=True, name="crosswalkBody"))
        self.orphaned = label(copy.get("settings.xw.orphaned"), role="note", tone="amber", wrap=True, name="crosswalkOrphaned")
        self.body.addWidget(self.orphaned)
        self.since = label("", role="note", wrap=True, name="crosswalkSince")
        self.counts = label("", role="caption", name="crosswalkCounts")
        self.body.addWidget(self.since)
        self.body.addWidget(self.counts)
        row = hbox(spacing=8)
        self.on_button = HeldAction("settings.xw.turn_on", "secondary")
        self.on_button.setObjectName("crosswalkOn")
        self.on_button.clicked.connect(lambda: self.turn_on())
        self.forget_button = HeldAction("settings.xw.forget", "secondary")
        self.forget_button.setObjectName("crosswalkForget")
        self.forget_button.clicked.connect(lambda: self.forget())
        for b in (self.on_button, self.forget_button):
            window.run_hold.register(b)
            row.addWidget(b)
        row.addStretch(1)
        self.body.addLayout(row)
        self.body.addWidget(label(copy.get("settings.xw.not_undoable"), role="caption", name="crosswalkNoUndo"))
        self.message = label("", role="note", wrap=True, name="crosswalkMessage")
        self.body.addWidget(self.message)

    @property
    def session(self):
        return getattr(self.window_.bridge, "session", None)

    def turn_on(self):
        s = self.session
        if s is None:
            return False
        if not (s.reviewer or "").strip():
            self.message.setText(copy.get("settings.xw.refused.reviewer_missing"))
            return False
        if not self.window_.confirm(copy.get("settings.xw.turn_on_title"),
                                    (copy.get("settings.xw.body"), copy.get("settings.xw.turn_on_line"),
                                     copy.get("settings.xw.not_undoable")),
                                    copy.get("settings.xw.turn_on"), copy.get("review.cancel")):
            return False
        xw.TurnOnCrosswalk(s.reviewer).run(s)
        self.message.setText("")
        self.window_.refresh()
        return True

    def forget(self):
        s = self.session
        if s is None:
            return False
        typed = self.window_.ask_text(copy.get("settings.xw.forget"), copy.get("settings.xw.forget_prompt"))
        if not xw.ForgetCrosswalk(typed or "").run(s):
            return False
        self.message.setText(copy.get("settings.xw.forgotten"))
        self.window_.refresh()
        return True

    def update_view(self, v):
        s = self.session
        st = xw.state(s) if s is not None else "off"
        self.state_tag.setText(copy.get("settings.xw.off") if st == "off" else "")
        self.state_tag.setVisible(st == "off")
        self.orphaned.setVisible(st == "orphaned")
        info = xw.summary(s) if st == "on" else None
        self.since.setVisible(info is not None)
        self.counts.setVisible(info is not None)
        if info is not None:
            at, by, c = info
            self.since.setText(copy.get("settings.xw.on_since", date=at[:10], name=by))
            self.counts.setText(copy.get("settings.xw.counts", people=c.people, pairs=c.pair_verdicts, groups=c.program_groups))
        self.on_button.setVisible(st == "off")
        self.forget_button.setVisible(st != "off")
