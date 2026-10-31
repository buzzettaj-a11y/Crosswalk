"""Measures, the suggested line, the joins check and known pairs (M13 CAL-3, CAL-4), hand-computed."""
from fractions import Fraction

from wholecount.engine.calibration.measure import joins_check, known_pairs_check, measure, suggest_line

LABELED = [(45, 1, "different"), (50, 1, "different"), (55, 1, "same"), (60, 1, "different"),
           (63, 2, "different"), (68, 2, "same"), (72, 2, "same"), (77, 2, "same"),
           (82, 3, "same"), (88, 3, "same"), (91, 3, "same"), (97, 3, "same"),
           (101, 4, "same"), (105, 4, "same"), (112, 4, "same"), (128, 4, "same")]


def test_hand_computed():
    m = measure({1: 100, 2: 50, 3: 20, 4: 10}, LABELED)
    assert [b.rate for b in m.bands] == [Fraction(1, 4), Fraction(3, 4), 1, 1]
    assert m.estimated_true == Fraction(185, 2)
    assert m.caught(62) == Fraction(135, 2) and m.recall(62) == Fraction(27, 37)
    assert suggest_line(m, 40, 98) == 55
    assert m.missed(62) == 25


def test_a_band_with_no_labels_is_unmeasured():
    m = measure({1: 100, 2: 50}, [(70, 2, "same")])
    assert m.bands[0].rate == "band_unmeasured"


def test_joins_check():
    assert joins_check(200, 1).result == "confirmed"
    assert joins_check(200, 2).result == "not_confirmed"
    assert joins_check(0, 0).result == "no_joins"
    assert joins_check(200, 1).n == 200


def test_known_pairs():
    keys = [f"{i:064x}" for i in range(200)]
    pairs = [(keys[2 * i], keys[2 * i + 1]) for i in range(50)]
    compared = {pairs[i]: 70 + i for i in range(44)}
    batch = set(keys[:96])
    k = known_pairs_check(pairs, compared, batch)
    assert (k.entered, len(k.compared), k.never_compared, k.not_in_batch) == (50, 44, 4, 2)
