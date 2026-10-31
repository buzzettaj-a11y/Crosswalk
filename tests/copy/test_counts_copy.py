"""H11: the not-final sentences for open copy groups and unconfirmed program proposals state what the counts carry."""
import pytest

from tests.fixtures.session import r_fixture
from tests.support.session import base
from wholecount import copy
from wholecount.session.runner import process


@pytest.mark.claim("CL-COUNT-08")
def test_copy_groups_open(tmp_path):
    c = base(tmp_path).counts()
    assert "copy_groups_open" in c.not_final_codes and c.open_copy_groups == 2 and c.goal1.low < c.goal1.high
    assert "range" in copy.get("counts.not_final.copy_groups_open", count=c.open_copy_groups)


@pytest.mark.claim("CL-COUNT-09")
def test_programs_unconfirmed(tmp_path):
    rows = r_fixture.r_rows()
    rows[0][8] = "housing"
    s = r_fixture.session(tmp_path, paths=r_fixture.files(tmp_path, r=rows))
    process(s)
    c = s.counts()
    assert "programs_unconfirmed" in c.not_final_codes and not c.final
    assert copy.get("counts.not_final.programs_unconfirmed", count=1)
