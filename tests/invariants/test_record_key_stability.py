"""H12: record keys don't depend on row position, so a re-export keeps every decision attached."""
from tests.fixtures.session import r_fixture
from wholecount.session.runner import process


def keys(tmp_path, rows):
    s = r_fixture.session(tmp_path, paths=r_fixture.files(tmp_path, r=rows))
    process(s)
    return {k: (r.value("Client_ID"), r.value("First_Name")) for k, r in s.results.rows.items()}


def test_reordered_and_extended(tmp_path):
    rows = r_fixture.r_rows()
    a = keys(tmp_path / "a", rows)
    b = keys(tmp_path / "b", list(reversed(rows)))
    c = keys(tmp_path / "c", [["R99", "New", "Person", "1999-09-09", "40 Oak St", "Brooklyn", "NY", "11201", "Youth"]] + rows)
    assert a == b and set(a) <= set(c)
