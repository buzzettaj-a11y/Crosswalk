"""Find tables in a literal grid, for layout tests."""
from wholecount.engine.read.accounting import account_grid
from wholecount.engine.read.model import Grid
from wholecount.engine.read.tables import find_tables


def grid(rows):
    width = max(len(r) for r in rows)
    return Grid(None, [list(r) + [""] * (width - len(r)) for r in rows])


def tables_of(rows):
    g = grid(rows)
    gt = find_tables(g)
    return gt.tables, gt.non_table_blocks, g


def accounting_of(rows, tables=None):
    g = grid(rows)
    gt = find_tables(g)
    return account_grid(g, tables if tables is not None else gt.tables, gt.non_table_blocks)


def a1(block):
    def col(i):
        n, out = i + 1, ""
        while n:
            n, r = divmod(n - 1, 26)
            out = chr(65 + r) + out
        return out
    return f"{col(block.c0)}{block.r0 + 1}:{col(block.c1)}{block.r1 + 1}"
