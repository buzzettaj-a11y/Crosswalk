"""COUNT-4 and fix plan 5.2 step 5: counted rows with a valid DOB over counted rows, and the warning below 100 percent."""
import pytest

from tests.fixtures.session import r_fixture
from wholecount import copy
from wholecount.session.runner import process


@pytest.mark.claim("CL-COUNT-04")
def test_coverage(tmp_path):
    rows = [["A1", "Ann", "North", "1980-01-01", "1 Oak St", "Brooklyn", "NY", "11201", "Housing"],
            ["A2", "Bea", "South", "", "2 Oak St", "Brooklyn", "NY", "11201", "Housing"]]
    s = r_fixture.session(tmp_path, paths=[r_fixture.write(tmp_path / "A.csv", rows)])
    process(s)
    num, den = s.counts().dob_coverage
    assert (num, den) == (1, 2)
    assert copy.get("counts.dob_coverage", percent=num * 100 // den).startswith("Date of birth on 50% of counted rows")
