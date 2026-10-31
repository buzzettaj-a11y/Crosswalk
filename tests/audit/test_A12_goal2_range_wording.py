"""A-12: Goal 2 showed one number while pairs were open. It now has a range and the same caveat code as Goal 1."""
import pytest

from tests.support.session import base
from wholecount import copy


@pytest.mark.claim("CL-COUNT-01")
@pytest.mark.claim("CL-COUNT-07")
def test_range_and_caveat(tmp_path):
    c = base(tmp_path).counts()
    assert c.goal2.low < c.goal2.high and c.goal1.low < c.goal1.high
    assert "pairs_open" in c.not_final_codes and not c.final
    assert copy.get("counts.range", low=c.goal2.low, high=c.goal2.high) == "9 to 11"
    assert "range" in copy.get("counts.not_final.pairs_open", count=c.open_pairs)
