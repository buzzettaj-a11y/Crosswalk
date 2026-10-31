"""ToneTag and BandWord (M12 section 0). Blue means needs you, green means a person decided, gray means settled. A same-person
band is plain ink text, never a colored tag, so color is never the only cue (SPEC 7.4)."""
from wholecount.ui.widgets.style import label
from wholecount.ui.widgets.tag import tag

TONES = {"needs_you": "needs", "decided": "confirmed", "settled": "neutral", "neutral": "neutral"}


def ToneTag(text, tone):  # noqa: N802  a widget factory, named like one
    w = tag(text, TONES[tone])
    w.setProperty("tone_tag", tone)
    return w


def BandWord(text):  # noqa: N802
    return label(text, role="band-word")
