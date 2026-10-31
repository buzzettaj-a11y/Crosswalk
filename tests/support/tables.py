"""Build a LoadedTable from literal headers and rows, for step and mapping tests."""
from tests.support.grids import grid
from wholecount.engine.read.tables import find_tables


def table(headers, rows):
    return find_tables(grid([headers] + [list(r) for r in rows])).tables[0]
