"""H4, the first balance: for any grid, every non-empty cell lands in exactly one block and the file accounting balances."""
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.grids import grid
from wholecount.engine.read.accounting import account_grid
from wholecount.engine.read.tables import find_tables, split_blocks

CELL = st.sampled_from(["", "", "", "ID", "First", "Last", "Total", "1", "11201", "Ana", "-", "Brooklyn"])
GRIDS = st.integers(1, 9).flatmap(lambda w: st.lists(st.lists(CELL, min_size=w, max_size=w), min_size=1, max_size=14))


@settings(max_examples=300, deadline=None)
@given(GRIDS)
def test_every_cell_in_one_block_and_balanced(rows):
    g = grid(rows)
    blocks = split_blocks(g)
    seen = set()
    for b in blocks:
        for r in range(b.r0, b.r1 + 1):
            for c in range(b.c0, b.c1 + 1):
                assert (r, c) not in seen
                seen.add((r, c))
    non_empty = {(r, c) for r, row in enumerate(g.rows) for c, v in enumerate(row) if v}
    assert non_empty <= seen
    gt = find_tables(g)
    a = account_grid(g, gt.tables, gt.non_table_blocks)
    assert a.balanced(), a


@settings(max_examples=150, deadline=None)
@given(GRIDS, st.data())
def test_balanced_whatever_is_ticked(rows, data):
    g = grid(rows)
    gt = find_tables(g)
    for t in gt.tables:
        t.included = data.draw(st.booleans())
        for b in t.blocks:
            b.included = data.draw(st.booleans())
    assert account_grid(g, gt.tables, gt.non_table_blocks).balanced()
