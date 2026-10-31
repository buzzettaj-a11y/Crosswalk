"""P-VAL-2 and fix plan 5.1: a row counts on person data alone. No address, a Hoboken ZIP and a Geosupport miss all count."""
from tests.fixtures.session import r_fixture
from wholecount.engine.geo.backend import NoBackend
from wholecount.session.runner import process

ROWS = [["P1", "Ann", "North", "1980-01-01", "", "", "", "", "Housing"],
        ["P2", "Bea", "South", "1981-01-01", "1 Hudson St", "Hoboken", "NJ", "07030", "Housing"],
        ["P3", "Cal", "East", "1982-01-01", "999 Nowhere Ave", "Brooklyn", "NY", "11201", "Housing"]]


def run(tmp_path, backend=None):
    s = r_fixture.session(tmp_path, backend=backend, paths=[r_fixture.write(tmp_path / "P.csv", ROWS)])
    process(s)
    return s


def test_all_three_count_and_balance(tmp_path):
    s = run(tmp_path)
    c = s.counts()
    assert c.counted == 3 and c.goal1.high == 3
    reasons = sorted(o.location.reason for o in s.results.outcomes.values())
    assert reasons == ["address_problem", "not_found", "outside_nyc"]
    assert c.locations.not_mapped == 3


def test_no_backend_reads_no_geocoder(tmp_path):
    s = run(tmp_path, NoBackend())
    reasons = {o.location.reason for o in s.results.outcomes.values() if o.location.reason not in ("address_problem", "outside_nyc")}
    assert reasons == {"no_geocoder"}
    assert s.counts().counted == 3
