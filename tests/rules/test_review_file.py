"""The review file and corrections coming back (SPEC 8.6): REVF-1 to REVF-5."""
import hashlib
import hmac

import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.review import cell, read_back, review_grid
from tests.support.session import rk
from wholecount import copy
from wholecount.engine.outputs.review_file import LOCKED, row_signature, run_id, share_key
from wholecount.engine.standardize.model import CountStatus
from wholecount.session import commands as C


def test_REVF_1_known_answers():
    mac = lambda m: hmac.new(bytes(range(32)), m, hashlib.sha256).digest()  # noqa: E731
    rid = run_id(mac, ["clinic_export_csv :: data :: 3380a5d7"])
    assert rid == "R-aec5efc922"
    assert row_signature(mac, rid, "7533705e667f8cf12288") == "3848ce28e083e70c"
    assert share_key(mac, "7533705e667f8cf12288") == "fa291d96e4"


def test_REVF_2_layout(tmp_path):
    s = session(tmp_path)
    grid = review_grid(s, tmp_path / "out")
    h = grid[0]
    assert h[:len(LOCKED)] == list(LOCKED)
    assert [c for c in h if c.endswith("_Zip")] == ["Original_Zip", "Standardized_Zip", "Corrected_Zip"]
    assert not any(c.startswith(("Original_Address", "Original_DOB", "Original_Program")) for c in h)
    r13 = rk(s, "R13")
    assert cell(grid, r13, "First_Name") == "" and cell(grid, r13, "Original_Zip") == "" and cell(grid, r13, "Corrected_Zip") == ""
    r14 = rk(s, "R14")
    assert cell(grid, r14, "Original_Zip") == ""


@pytest.mark.claim("CL-CORR-01")
@pytest.mark.claim("CL-CORR-04")
def test_REVF_3_refusals(tmp_path):
    s = session(tmp_path)
    grid = review_grid(s, tmp_path / "out")
    r13, r14 = rk(s, "R13"), rk(s, "R14")
    cell(grid, r13, "Corrected_Zip", "11201")
    cell(grid, r14, "Corrected_Zip", "11201")
    got = read_back(s, grid, tmp_path / "back.csv")
    assert [c.record_key for c in got.accepted] == [r13]
    assert [(x.record_key, x.code, x.column) for x in got.refused] == [(r14, "field_not_failing", "Zip")]
    assert copy.get(got.refused[0].sentence_key)
    other = lambda m: hmac.new(bytes(range(32, 64)), m, hashlib.sha256).digest()  # noqa: E731
    got = read_back(s, grid, tmp_path / "back2.csv", mac=other)
    assert {x.code for x in got.refused} == {"signature_wrong"}


def test_REVF_4_accepted_corrections_apply(tmp_path):
    s = session(tmp_path)
    grid = review_grid(s, tmp_path / "out")
    r13 = rk(s, "R13")
    cell(grid, r13, "Corrected_Zip", "11201")
    got = read_back(s, grid, tmp_path / "back.csv")
    s.history.execute(C.ApplyCorrections(got.accepted, got.fingerprint, got.file_name))
    assert s.results.outcomes[r13].count_status == CountStatus.COUNTED_CORRECTED


def test_REVF_5_correction_entry_holds_hashes_only(tmp_path):
    s = session(tmp_path)
    grid = review_grid(s, tmp_path / "out")
    cell(grid, rk(s, "R13"), "Corrected_Zip", "11201")
    got = read_back(s, grid, tmp_path / "back.csv")
    s.history.execute(C.ApplyCorrections(got.accepted, got.fingerprint, got.file_name))
    e = s.audit[-1]
    assert e.code == "CORRECTION" and e.get("field_name") == ["Zip"] and e.get("file_name") == ["back.csv"]
    assert "11201" not in repr(e)
