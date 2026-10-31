"""Counting and the balance (SPEC 7.1 to 7.3, H4). Goal 1 and Goal 2 come with ranges; both balances must hold.

Only counted rows enter the counts. Address fields play no part in whether a row counts (P-VAL-2).
"""
from dataclasses import dataclass, field

from wholecount.engine.programs import people_without_program
from wholecount.engine.standardize.model import CountStatus


@dataclass(frozen=True)
class Range:
    low: int
    high: int

    @property
    def single(self):
        return self.low == self.high


@dataclass(frozen=True)
class Locations:
    high: int = 0
    low: int = 0
    no_fixed_address: int = 0
    outside_nyc: int = 0
    address_problem: int = 0
    not_found: int = 0
    no_geocoder: int = 0
    filled: int = 0

    @property
    def mapped(self):
        return self.high + self.low

    @property
    def not_mapped(self):
        return self.no_fixed_address + self.outside_nyc + self.address_problem + self.not_found + self.no_geocoder

    @property
    def looked_up(self):
        return self.mapped + self.not_found


@dataclass(frozen=True)
class Counts:
    goal1: Range
    goal2: Range
    per_program: dict
    people_without_program: Range
    open_pairs: int
    open_copy_groups: int
    received: int
    counted: int
    not_counted_yet: int
    set_aside: int
    locations: Locations
    final: bool
    not_in_goal2: tuple = ()
    dob_coverage: tuple = (0, 0)
    matched_from_earlier: int | None = None
    not_final_codes: tuple = ()           # why the count isn't final, for the copy (A-06, A-12)


@dataclass(frozen=True)
class TableBalance:
    table_key: str
    received: int
    counted: int
    not_counted_yet: int
    set_aside: int
    mapped: int
    counted_not_mapped: int


@dataclass(frozen=True)
class Balance:
    tables: tuple
    excluded_rows: int
    non_table_rows: int
    above_header_rows: int
    header_rows: int
    file_rows: int

    def total(self, name):
        return sum(getattr(t, name) for t in self.tables)


class BalanceError(Exception):
    def __init__(self, check, numbers):
        super().__init__(check)
        self.check = check
        self.numbers = numbers


def locations_of(outcomes):
    tally = {k: 0 for k in Locations.__dataclass_fields__}
    for o in outcomes:
        if not o.counted or o.location is None:
            continue
        loc = o.location
        if loc.kind == "mapped":
            tally[loc.confidence] += 1
        else:
            tally[loc.reason] += 1
        if loc.filled:
            tally["filled"] += 1
    return Locations(**tally)


def balance_of(outcomes, accounting):
    """accounting: dict with excluded_rows, non_table_rows, above_header_rows, header_rows and file_rows (M01)."""
    by_table = {}
    for o in outcomes:
        by_table.setdefault(o.table_key, []).append(o)
    tables = []
    for tk in sorted(by_table):
        os_ = by_table[tk]
        counted = [o for o in os_ if o.counted]
        mapped = sum(1 for o in counted if o.location is not None and o.location.kind == "mapped")
        tables.append(TableBalance(tk, len(os_), len(counted), sum(1 for o in os_ if o.count_status == CountStatus.NOT_COUNTED_YET),
                                   sum(1 for o in os_ if o.count_status == CountStatus.SET_ASIDE), mapped, len(counted) - mapped))
    return Balance(tuple(tables), **accounting)


def assert_balance(balance, outcomes=None):
    """COUNT-5. Raises BalanceError with the numbers when a check fails."""
    for t in balance.tables:
        if t.received != t.counted + t.not_counted_yet + t.set_aside:
            raise BalanceError("rows", {"table": t.table_key, "received": t.received, "counted": t.counted,
                                        "not_counted_yet": t.not_counted_yet, "set_aside": t.set_aside})
        if t.counted != t.mapped + t.counted_not_mapped:
            raise BalanceError("locations", {"table": t.table_key, "counted": t.counted, "mapped": t.mapped,
                                             "counted_not_mapped": t.counted_not_mapped})
    if outcomes is not None:
        locs = locations_of(outcomes)
        if locs.mapped + locs.not_mapped != balance.total("counted"):
            raise BalanceError("locations", {"counted": balance.total("counted"), "mapped": locs.mapped,
                                             "not_mapped": locs.not_mapped})
    placed = (balance.total("received") + balance.excluded_rows + balance.non_table_rows + balance.above_header_rows
              + balance.header_rows)
    if placed != balance.file_rows:
        raise BalanceError("files", {"received": balance.total("received"), "excluded": balance.excluded_rows,
                                     "non_table": balance.non_table_rows, "above_header": balance.above_header_rows,
                                     "header": balance.header_rows, "file_rows": balance.file_rows})


def balance_lines(balance):
    """The two equations every screen and file uses (A-22): (copy key, int parameters)."""
    return (("balance.rows", {"received": balance.total("received"), "counted": balance.total("counted"),
                              "not_counted_yet": balance.total("not_counted_yet"), "set_aside": balance.total("set_aside")}),
            ("balance.locations", {"counted": balance.total("counted"), "mapped": balance.total("mapped"),
                                   "not_mapped": balance.total("counted_not_mapped")}))


def _pairs(records, master, program):
    return {(master[rk], program[rk]) for rk in records if program.get(rk)}


def count(outcomes, identity, person_of_record, program_of_record, open_pairs, open_copy_groups, unconfirmed_programs=0,
          stale=False, not_in_goal2=(), dob_valid=frozenset()):
    """COUNT-1 to COUNT-4. program_of_record holds canonical program names (M07) for counted rows."""
    counted = [o.record_key for o in outcomes if o.counted]
    high_master = identity.master_of_record
    low_master = {rk: identity.low_master_of[person_of_record[rk]] for rk in counted}
    hi, lo = _pairs(counted, high_master, program_of_record), _pairs(counted, low_master, program_of_record)
    programs = sorted({p for _, p in hi})
    per_program = {p: Range(len({m for m, q in lo if q == p}), len({m for m, q in hi if q == p})) for p in programs}
    nyc = sum(1 for o in outcomes if o.count_status == CountStatus.NOT_COUNTED_YET)
    codes = []
    if nyc:
        codes.append("rows_not_counted_yet")
    if open_pairs:
        codes.append("pairs_open")
    if open_copy_groups:
        codes.append("copy_groups_open")
    if unconfirmed_programs:
        codes.append("programs_unconfirmed")
    if stale:
        codes.append("stale")
    rp = {rk: program_of_record.get(rk) for rk in counted}
    return Counts(
        goal1=Range(identity.low, identity.settled),
        goal2=Range(len(lo), len(hi)),
        per_program=per_program,
        people_without_program=Range(people_without_program({rk: low_master[rk] for rk in counted}, rp),
                                     people_without_program({rk: high_master[rk] for rk in counted}, rp)),
        open_pairs=open_pairs,
        open_copy_groups=open_copy_groups,
        received=len(outcomes),
        counted=len(counted),
        not_counted_yet=nyc,
        set_aside=sum(1 for o in outcomes if o.count_status == CountStatus.SET_ASIDE),
        locations=locations_of(outcomes),
        final=not codes,
        not_in_goal2=tuple(not_in_goal2),
        dob_coverage=(sum(1 for rk in counted if rk in dob_valid), len(counted)),
        not_final_codes=tuple(codes),
    )
