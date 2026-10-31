"""Reading a returned review file (SPEC 8.6, C-06, A-10). Rows match by Record_Key. A row is accepted only if it carries this
computer's signature, its originals are unchanged, no locked cell changed, and it corrects only fields that failed on it.
Nothing is guessed; a refused row changes nothing and the rest of the file still applies.
"""
from dataclasses import dataclass

from wholecount.engine.corrections import VerifiedCorrection
from wholecount.engine.outputs.review_file import LOCKED, failing_fields, review_fields, review_row, row_signature

SENTENCE = {"signature_missing": "corrections.refused.signature", "signature_wrong": "corrections.refused.signature",
            "originals_changed": "corrections.refused.changed", "unknown_record": "corrections.refused.changed",
            "other_column_changed": "corrections.refused.other_column", "field_not_failing": "corrections.refused.field_not_failing",
            "not_a_review_file": "corrections.refused.not_a_review_file", "duplicate_in_file": "corrections.refused.duplicate",
            "row_set_aside": "corrections.refused.set_aside"}


@dataclass(frozen=True)
class Refusal:
    line: int | None
    record_key: str | None
    code: str
    column: str | None = None

    @property
    def sentence_key(self):
        return SENTENCE[self.code]


@dataclass(frozen=True)
class CorrectionsRead:
    accepted: tuple = ()                  # VerifiedCorrection
    refused: tuple = ()                   # Refusal
    rows_read: int = 0
    no_corrections: bool = False
    file_name: str = ""
    fingerprint: str = ""
    lines: tuple = ()                     # (record key, line) for accepted rows


def read_corrections(grid, mac, view, file_name, fingerprint):
    """grid: the file's rows as text, header first, as M01's reader gives them."""
    if not grid:
        return CorrectionsRead(refused=(Refusal(None, None, "not_a_review_file"),), file_name=file_name, fingerprint=fingerprint)
    header = [h.strip() for h in grid[0]]
    if not {"Record_Key", "Run_ID", "Signature"} <= set(header):
        return CorrectionsRead(refused=(Refusal(None, None, "not_a_review_file"),), file_name=file_name, fingerprint=fingerprint)
    rows_by_key = {r.record_key: r for r in view.rows}
    fields = review_fields(view)
    accepted, refused, lines = [], [], []
    for i, cells in enumerate(grid[1:], start=2):
        d = {h: (cells[j] if j < len(cells) else "").strip() for j, h in enumerate(header)}
        corrected = {h[len("Corrected_"):]: v for h, v in d.items() if h.startswith("Corrected_") and v}
        if not corrected:
            continue
        rk = d.get("Record_Key", "")
        if not d.get("Signature"):
            refused.append(Refusal(i, rk, "signature_missing"))
            continue
        if d.get("Run_ID") != view.run_id or d["Signature"] != row_signature(mac, view.run_id, rk):
            refused.append(Refusal(i, rk, "signature_wrong"))
            continue
        r = rows_by_key.get(rk)
        if r is None:
            refused.append(Refusal(i, rk, "unknown_record"))
            continue
        expected = review_row(view, r, fields)
        changed_original = next((h for h in header if h.startswith("Original_") and d[h] != expected.get(h, "")), None)
        if changed_original:
            refused.append(Refusal(i, rk, "originals_changed", changed_original))
            continue
        # A changed locked cell or a correction to a field that didn't fail is refused on its own and never read as a value.
        # The row's other corrections still apply, because the signature and the originals proved where the row came from.
        for h in header:
            if (h in LOCKED or h.startswith("Standardized_")) and d[h] != expected.get(h, d[h]):
                refused.append(Refusal(i, rk, "other_column_changed", h))
        failing = set(failing_fields(r))
        for f in sorted(corrected):
            if f not in failing:
                refused.append(Refusal(i, rk, "field_not_failing", f))
        good = {f: v for f, v in corrected.items() if f in failing}
        if good:
            accepted.append(VerifiedCorrection(rk, tuple(sorted(good.items()))))
            lines.append((rk, i))
    return CorrectionsRead(tuple(accepted), tuple(refused), len(grid) - 1, not accepted and not refused, file_name, fingerprint,
                           tuple(lines))
