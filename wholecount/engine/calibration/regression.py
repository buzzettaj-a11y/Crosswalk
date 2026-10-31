"""Re-scoring stored labeled pairs under the weights in force (M13 CAL-6)."""
from dataclasses import dataclass

from wholecount.engine.identity import score_from_codes


@dataclass(frozen=True)
class Ratio:
    num: int
    den: int

    def lower_than(self, other):
        """Cross-multiplied, so no float is involved. An empty ratio is never lower."""
        if not self.den or not other.den:
            return False
        return self.num * other.den < other.num * self.den


@dataclass(frozen=True)
class Regression:
    caught_before: Ratio        # Same pairs at or above the line, over all Same pairs
    caught_after: Ratio
    precision_before: Ratio     # Same pairs over all pairs at or above the line
    precision_after: Ratio

    @property
    def dropped(self):
        return self.caught_after.lower_than(self.caught_before) or self.precision_after.lower_than(self.precision_before)


def rates(pairs, line):
    """pairs: (score, label). Returns (caught, precision) as Ratios."""
    same = [s for s, lab in pairs if lab == "same"]
    above = [lab for s, lab in pairs if s >= line]
    return Ratio(sum(1 for s in same if s >= line), len(same)), Ratio(sum(1 for lab in above if lab == "same"), len(above))


def regression_check(stored, weights, line):
    """stored: StoredLabels. Re-scores each pair from its codes and compares with the baseline taken at labeling time."""
    before = [(p.score, p.label) for p in stored.pairs]
    after = [(score_from_codes(p.codes, weights), p.label) for p in stored.pairs]
    cb, pb = rates(before, stored.baseline_line if stored.baseline_line is not None else line)
    ca, pa = rates(after, line)
    return Regression(cb, ca, pb, pa)
