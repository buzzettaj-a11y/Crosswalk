"""The fast path has no code of its own: it gives the staged route's results, stops at Programs while a proposal is open, and
blocks on an unmapped required field."""
import pytest

from tests.fixtures.session import r_fixture
from tests.support.session import base
from wholecount.engine.programs import StopAtPrograms
from wholecount.session import commands as C
from wholecount.session.runner import Blocked, fast_path


def test_equal(tmp_path):
    a = base(tmp_path / "a")
    b = r_fixture.session(tmp_path / "b")
    fast_path(b)
    assert a.results.digest() == b.results.digest()


def test_stops_at_programs(tmp_path):
    rows = r_fixture.r_rows()
    rows[0][8] = "housing"
    s = r_fixture.session(tmp_path, paths=r_fixture.files(tmp_path, r=rows))
    gate = fast_path(s)
    assert isinstance(gate, StopAtPrograms) and gate.unconfirmed == 1
    s.history.execute(C.DecideProgramGroup("confirm", ("Housing", "housing")))
    assert not isinstance(fast_path(s), StopAtPrograms)


def test_blocks_on_a_missing_required_field(tmp_path):
    rows = [[r[1], r[2], r[4]] for r in r_fixture.r_rows()]
    path = r_fixture.write(tmp_path / "N.csv", rows, ["First_Name", "Last_Name", "Address_1"])
    s = r_fixture.session(tmp_path, paths=[path])
    with pytest.raises(Blocked) as e:
        fast_path(s)
    assert e.value.field == "Client_ID"
