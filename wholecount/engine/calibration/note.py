"""What a saved calibration says on screen and in the methods note (M13 CAL-8)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationNote:
    calibrated_at: str          # the date, YYYY-MM-DD
    bands: tuple                # (band, labeled, same)
    joins: tuple                # (n, wrong, result)
    line: int                   # the proposal line in force
    recall_pct: int | None      # the estimated share of true matches at that line, whole percent, rounded down
    matches_weights: bool       # False when the weights changed since the labels were made
