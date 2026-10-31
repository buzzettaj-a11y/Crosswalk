"""What reading a file produces (P-READ). Every value is text; nothing is converted on the way in."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CellMeta:
    """Kept only for numeric and date .xlsx cells, so a real date cell can be recognized later (P-STD-6)."""

    kind: str               # "number" or "date"
    number_format: str


@dataclass
class Grid:
    """One sheet (or the whole of a text file) as rectangular cleaned text. Row i is file row i + 1."""

    sheet: str | None
    rows: list
    meta: dict = field(default_factory=dict)     # (row, col) -> CellMeta, 0-based
    hidden: bool = False
    fixed_header: list | None = None             # JSON and XML: the keys, which are the header


@dataclass(frozen=True)
class Block:
    """A rectangle of the grid, 0-based and inclusive."""

    r0: int
    r1: int
    c0: int
    c1: int

    @property
    def n_rows(self):
        return self.r1 - self.r0 + 1

    @property
    def n_cols(self):
        return self.c1 - self.c0 + 1


@dataclass
class BlockInfo:
    block: Block
    rows: int                 # data rows this block gives its table
    included: bool = True
    continuation: bool = False


@dataclass
class LoadedTable:
    key: str
    letter: str
    sheet: str | None
    blocks: list                                 # BlockInfo, the first one primary
    header_row: int                              # 1-based inside the first block, 0 for none
    header_is_virtual: bool
    raw_headers: list
    headers: list
    rows: list                                   # data rows, every block, cleaned text
    row_numbers: list                            # file row number of each data row
    row_block: list                              # index into blocks for each data row
    meta: dict                                   # (data row index, col) -> CellMeta
    record_keys: list
    kind: str                                    # records, summary or unknown
    kind_reason: str
    included: bool
    suggested_header_row: int | None = None
    header_warning: str | None = None
    above_header_rows: int = 0
    empty_columns: list = field(default_factory=list)
    sensitive_dropped: list = field(default_factory=list)
    sensitive_by_values: int = 0
    source_rows: list = field(default_factory=list, repr=False)   # every row of every block as read, for a header change

    @property
    def included_row_count(self):
        if not self.included:
            return 0
        return sum(b.rows for b in self.blocks if b.included)

    @property
    def excluded_row_count(self):
        return sum(b.rows for b in self.blocks) - self.included_row_count

    def is_row_included(self, i):
        return self.included and self.blocks[self.row_block[i]].included


@dataclass
class ReadFile:
    name: str
    extension: str
    fingerprint: str
    size: int
    encoding: str | None
    encoding_samples: list
    grids: list
    clean_counts: dict
    replacement_chars: int = 0


UNREADABLE_REASONS = (
    "unsupported_type", "unreadable_encoding", "bad_workbook", "bad_json", "bad_xml", "empty_file", "blocked_by_guard",
)


class UnreadableFile(Exception):
    """A file that can't be read. Carries a reason ID only, never text from the file."""

    def __init__(self, reason_id):
        if reason_id not in UNREADABLE_REASONS:
            raise ValueError(reason_id)
        super().__init__(reason_id)
        self.reason_id = reason_id
