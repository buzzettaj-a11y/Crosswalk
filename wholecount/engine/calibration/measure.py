"""Exact measures from the settled labels (M13 CAL-3, CAL-4). Counts and fractions.Fraction only."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class BandMeasure:
    band: int
    population: int
    labeled: int
    same: int

    @property
    def rate(self):
        """same / labeled, or band_unmeasured when nothing in the band was labeled."""
        return Fraction(self.same, self.labeled) if self.labeled else "band_unmeasured"


@dataclass(frozen=True)
class Measures:
    bands: tuple                    # BandMeasure, band 1 first
    estimated_true: Fraction
    labeled_same: tuple             # (score, band) for each labeled Same pair

    def caught(self, line):
        by = {m.band: m for m in self.bands}
        total = Fraction(0)
        for b, m in by.items():
            if m.labeled:
                n = sum(1 for s, bb in self.labeled_same if bb == b and s >= line)
                total += Fraction(m.population * n, m.labeled)
        return total

    def recall(self, line):
        return self.caught(line) / self.estimated_true if self.estimated_true else Fraction(0)

    def missed(self, line):
        return self.estimated_true - self.caught(line)


def measure(populations, settled_pairs):
    """populations: band -> pairs in the batch. settled_pairs: (score, band, label) for each settled pair, joins excluded."""
    bands, est, same_list = [], Fraction(0), []
    for b in sorted(populations):
        rows = [(s, lab) for s, bb, lab in settled_pairs if bb == b]
        labeled = len(rows)
        same = sum(1 for _, lab in rows if lab == "same")
        bands.append(BandMeasure(b, populations[b], labeled, same))
        if labeled:
            est += Fraction(populations[b] * same, labeled)
        same_list += [(s, b) for s, lab in rows if lab == "same"]
    return Measures(tuple(bands), est, tuple(same_list))


def suggest_line(measures, floor, target_pct, top=200):
    """The largest line in [floor, top] whose recall is at least target_pct%, or None when there's nothing to measure."""
    if not measures.estimated_true:
        return None
    best = None
    for line in range(floor, top + 1):
        if measures.recall(line) * 100 >= target_pct:
            best = line
    return best


@dataclass(frozen=True)
class JoinsCheck:
    n: int
    wrong: int
    result: str             # confirmed, not_confirmed or no_joins


def joins_check(n, wrong, target_tenths=995):
    if n <= 0:
        return JoinsCheck(n, wrong, "no_joins")
    ok = wrong * 1000 <= n * (1000 - target_tenths)
    return JoinsCheck(n, wrong, "confirmed" if ok else "not_confirmed")


@dataclass(frozen=True)
class KnownPairsCheck:
    entered: int
    not_in_batch: int
    compared: tuple         # (a, b, score)
    never_compared: int


def known_pairs_check(pairs, compared, batch_keys):
    """pairs: (person key a, person key b) per known pair. compared: (a, b) -> score from the calibration pass."""
    batch_keys = set(batch_keys)
    out, missing, never = [], 0, 0
    for a, b in pairs:
        lo, hi = sorted((a, b))
        if lo not in batch_keys or hi not in batch_keys:
            missing += 1
        elif (lo, hi) in compared:
            out.append((lo, hi, compared[(lo, hi)]))
        else:
            never += 1
    return KnownPairsCheck(len(pairs), missing, tuple(out), never)
