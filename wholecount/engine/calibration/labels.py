"""Two labelers' labels, their disagreements and the settled set (M13 CAL-2)."""
from dataclasses import dataclass, field

LABELS = ("same", "different", "unsure")


@dataclass
class LabelSet:
    labeler: str
    labels: dict = field(default_factory=dict)      # pair ID -> same, different or unsure
    finished: bool = False

    def label(self, pair_id, value):
        if value not in LABELS:
            raise ValueError(value)
        self.labels[pair_id] = value


def disagreements(a, b):
    """Every pair whose two labels differ, Unsure against Same included."""
    return sorted(p for p in set(a.labels) | set(b.labels) if a.labels.get(p) != b.labels.get(p))


@dataclass(frozen=True)
class Settlement:
    labels: dict            # pair ID -> same or different
    dropped: tuple          # pair IDs dropped: Unsure for both, or still Unsure after settling


def settle(a, b, settled):
    """settled: pair ID -> the label both labelers chose together for a disagreement."""
    out, dropped = {}, []
    for p in sorted(set(a.labels) | set(b.labels)):
        la, lb = a.labels.get(p), b.labels.get(p)
        final = la if la == lb else settled.get(p)
        if final in ("same", "different"):
            out[p] = final
        else:
            dropped.append(p)
    return Settlement(out, tuple(dropped))
