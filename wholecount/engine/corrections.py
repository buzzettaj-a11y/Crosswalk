"""Applying verified corrections (SPEC 6.6 P-REV-6, C-06). M09 verifies the signed review file; this applies what it passes on.

A row is matched by record key, never by position or range. The new text goes through P-STD and P-VAL. A row that now counts
is counted_corrected; a row that still fails stays not counted yet with its new reasons.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedCorrection:
    record_key: str
    fields: tuple                         # (field, new standardized text)


@dataclass(frozen=True)
class CorrectionReport:
    accepted: tuple = ()                  # (record key, (field, ...))
    refused: tuple = ()                   # (code, record key)
    changed_rows: dict = None             # record key -> new StdRow (memory only)
    old_new: tuple = ()                   # (record key, field, old text, new text), memory only, for value hashes


def apply_corrections(corrections, records, fingerprint, restandardize):
    """records: record key -> (StdRow, set_aside flag). restandardize(record_key, {field: text}) -> new StdRow."""
    seen, accepted, refused, changed, old_new = set(), [], [], {}, []
    dup = {c.record_key for c in corrections if sum(1 for x in corrections if x.record_key == c.record_key) > 1}
    for c in corrections:
        if c.record_key in dup:
            if c.record_key not in seen:
                refused.append(("duplicate_in_file", c.record_key))
                seen.add(c.record_key)
            continue
        if c.record_key not in records:
            refused.append(("unknown_record", c.record_key))
            continue
        row, aside = records[c.record_key]
        if aside:
            refused.append(("row_set_aside", c.record_key))
            continue
        diff = {f: t for f, t in c.fields if row.value(f) != t}
        if not diff:
            continue
        changed[c.record_key] = restandardize(c.record_key, diff)
        accepted.append((c.record_key, tuple(sorted(diff))))
        old_new += [(c.record_key, f, row.value(f), t) for f, t in sorted(diff.items())]
    return CorrectionReport(tuple(accepted), tuple(refused), changed, tuple(old_new))
