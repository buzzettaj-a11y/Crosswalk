"""P-READ-7 and H4: every non-empty row in a file is in an included table, an excluded table, a non-table block, a header row or
above a header. Side-by-side tables share file rows, so one file row can be counted once per block; shared_rows is that extra."""
from dataclasses import dataclass


@dataclass
class FileAccounting:
    non_empty_rows: int = 0
    shared_rows: int = 0
    header: int = 0
    above_header: int = 0
    included: int = 0
    excluded: int = 0
    non_table: int = 0
    non_empty_cells: int = 0
    cells_in_blocks: int = 0

    def balanced(self):
        placed = self.header + self.above_header + self.included + self.excluded + self.non_table
        return placed == self.non_empty_rows + self.shared_rows and self.cells_in_blocks == self.non_empty_cells

    @property
    def rows_left_out(self):
        """Rows that won't be counted because their table or block isn't included. Nonzero is a warning the screen shows (C-23)."""
        return self.excluded + self.non_table

    def add(self, other):
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))
        return self


def _cells(grid, b):
    return sum(1 for r in range(b.r0, b.r1 + 1) for c in range(b.c0, min(b.c1, len(grid.rows[r]) - 1) + 1) if grid.rows[r][c])


def account_grid(grid, tables, non_table_blocks):
    """The accounting for one grid. tables are this grid's LoadedTables, non_table_blocks its other Blocks."""
    a = FileAccounting()
    a.non_empty_rows = sum(1 for r in grid.rows if any(r))
    a.non_empty_cells = sum(1 for r in grid.rows for c in r if c)
    covered, block_rows = set(), 0
    for t in tables:
        virtual = 1 if t.header_is_virtual else 0
        if t.header_row and not virtual:
            a.header += 1
        a.above_header += t.above_header_rows
        a.included += t.included_row_count
        a.excluded += t.excluded_row_count
        for bi in t.blocks:
            b = bi.block
            covered.update(range(b.r0, b.r1 + 1))
            block_rows += b.n_rows
            a.cells_in_blocks += _cells(grid, b)
    for b in non_table_blocks:
        a.non_table += b.n_rows
        covered.update(range(b.r0, b.r1 + 1))
        block_rows += b.n_rows
        a.cells_in_blocks += _cells(grid, b)
    a.shared_rows = block_rows - len(covered)
    return a
