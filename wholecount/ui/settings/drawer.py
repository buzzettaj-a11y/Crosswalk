"""Puts M13's four cards into M10's SettingsDrawer (SPEC 11.3). No second Settings link."""
from wholecount.ui.settings.crosswalk import CrosswalkCard
from wholecount.ui.settings.matching import MeasureCard
from wholecount.ui.settings.secret import SecretCard
from wholecount.ui.settings.thresholds import LinesCard


class SettingsSections:
    def __init__(self, window):
        self.secret = SecretCard(window)
        self.crosswalk = CrosswalkCard(window)
        self.lines = LinesCard(window)
        self.measure = MeasureCard(window)
        for c in self.cards:
            window.settings.sections.addWidget(c)

    @property
    def cards(self):
        return (self.secret, self.crosswalk, self.lines, self.measure)

    def update_view(self, v):
        for c in self.cards:
            c.update_view(v)


def install(window):
    return SettingsSections(window)
