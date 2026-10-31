"""The default reviewer is the injected getuser result, and every decision stores the name (8.7)."""
from tests.support.session import base, rk
from wholecount.session import commands as C


def test_default_comes_from_getuser(tmp_path):
    s = base(tmp_path)
    assert s.reviewer == "Joe"
    s.history.execute(C.SetAsideRows([rk(s, "R01")], "test_record"))
    assert all(d.reviewer == "Joe" for d in s.decisions)
