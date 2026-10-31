"""COUNT-6: a corrupted Results raises BalanceError for each of the three checks."""
import dataclasses

import pytest

from tests.support.session import base
from wholecount.engine.counts import BalanceError


@pytest.mark.parametrize("check", ["rows", "locations", "files"])
def test_each_check(tmp_path, check):
    s = base(tmp_path)
    b = s.results.balance
    t = b.tables[0]
    if check == "rows":
        s.results.balance = dataclasses.replace(b, tables=(dataclasses.replace(t, received=t.received + 1),) + b.tables[1:])
    elif check == "locations":
        s.results.balance = dataclasses.replace(b, tables=(dataclasses.replace(t, mapped=t.mapped + 1),) + b.tables[1:])
    else:
        s.results.balance = dataclasses.replace(b, header_rows=b.header_rows + 1)
    with pytest.raises(BalanceError) as e:
        s.counts()
    assert e.value.check == check
    assert s.download_gate().reasons[0] == "balance_failed"
