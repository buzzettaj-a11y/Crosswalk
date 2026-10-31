"""Every text and background pair the frame uses meets WCAG contrast: 4.5, or 3.0 for text at 24px and above."""
import pytest

from wholecount.ui.theme import TEXT_PAIRS, color

LARGE = set()                             # no pair here is only used at 24px and above


def _hex(name):
    return name if name.startswith("#") else color(name)


def luminance(hex_):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def ratio(a, b):
    la, lb = sorted((luminance(_hex(a)), luminance(_hex(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("fg,bg", TEXT_PAIRS)
def test_pair_meets_contrast(fg, bg):
    need = 3.0 if (fg, bg) in LARGE else 4.5
    assert ratio(fg, bg) >= need, (fg, bg, round(ratio(fg, bg), 2))


def test_ratio_negative_control():
    assert ratio("#ffffff", "#ffffff") == 1.0
    assert ratio("#000000", "#ffffff") > 20
