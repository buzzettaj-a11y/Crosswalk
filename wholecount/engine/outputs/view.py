"""OutputView: everything the files, logs, summary and receipt need, as plain frozen data (SPEC 9). No secret and no Qt.

The session builds it after Session.counts() passed. Values that need the install secret (moved points, the review file's
signatures, the shareable log's hashes) are computed there and arrive here finished.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutRow:
    record_key: str
    table_key: str
    letter: str
    file_name: str
    sheet: str | None
    row_number: int
    system: str
    count_status: str                     # CountStatus value
    location: tuple | None                # (kind, confidence, reason, filled) for counted rows
    values: tuple                         # ((field, standardized text), ...) mapped fields only
    originals: tuple                      # ((field, entered text), ...)
    reasons: tuple                        # open reason IDs
    reason_fields: tuple                  # (reason ID, field)
    set_aside_reason: str | None
    kept_record_key: str | None
    in_copy_group: bool
    copy_others: tuple
    open_copy_kind: str | None            # identical or possible while the row's copy group is open
    master_id: str | None                 # high end
    program: str                          # canonical program, or ""
    districts: tuple | None               # (senate, assembly, council) from the true point
    point: tuple | None                   # (lat, lon), the true point, memory only
    address_key: str = ""
    signature: str = ""                   # review file signature

    def value(self, f):
        return dict(self.values).get(f, "")

    def original(self, f):
        return dict(self.originals).get(f, "")

    @property
    def counted(self):
        return self.count_status in ("counted_passed", "counted_approved", "counted_corrected")


@dataclass(frozen=True)
class TableSummary:
    table_key: str
    letter: str
    file_name: str
    sheet: str | None
    number: int                           # table number within its letter
    encoding: str
    invisible_removed: int


@dataclass(frozen=True)
class OutputView:
    practice: bool
    backend: str
    release: str
    offset_applied: bool
    fields: tuple                         # mapped field keys in schema order, canonical then custom
    rows: tuple                           # OutRow, every received row
    masters: tuple                        # (master ID, (record keys in table order), match confidence word key)
    tables: tuple                         # TableSummary
    sources: tuple                        # (letter, file name, system display name), add order
    counts: object
    balance: object
    confidence: object
    map_entries: tuple = ()               # MapEntry, one per (master, program) at the high end
    map_points: tuple = ()                # MapPoint, already moved
    run_id: str = ""
    events: tuple = ()                    # (time ISO, AuditEntry)
    share_keys: dict = field(default_factory=dict)   # record key -> second keyed hash (shareable log)
    reviewer_counts: tuple = ()
    problem_ids: tuple = ()               # problems.toml order
    calibration: object = None            # M13


@dataclass(frozen=True)
class ExportSettings:
    formats: dict = field(default_factory=dict)          # file name -> "csv", "xlsx" or "json"; CSV when unset
    columns_off: dict = field(default_factory=dict)      # FileId -> frozenset of columns switched off (OUT-1)
    map_points: bool = False                             # Map_Points is off by default (P-GEO-6)
    exact_coordinates: bool = False                      # Latitude and Longitude in Final_Clean_Mapped, for internal use
    include_file_names: bool = False                     # the printable summary's sources section
