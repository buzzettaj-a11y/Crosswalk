"""C-06, the file-level cases (with M08): the review file's signature, originals and locked cells, and matching by key."""
import hashlib
import hmac

import pytest

from tests.audit.test_C06_corrections_by_record_key import ROWS
from tests.support.files_run import run, write_csv
from tests.support.review import cell, read_back, review_grid
from wholecount import copy
from wholecount.session import commands as C

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]


@pytest.fixture()
def setup(tmp_path):
    s = run(tmp_path, [write_csv(tmp_path / "in" / "A.csv", COLS, ROWS)])
    grid = review_grid(s, tmp_path / "out")
    a900 = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "A900")
    return s, grid, a900


def test_case_1_accepted(tmp_path, setup):
    s, grid, a900 = setup
    cell(grid, a900, "Corrected_Zip", "11201")
    got = read_back(s, grid, tmp_path / "r.csv")
    assert [c.record_key for c in got.accepted] == [a900] and got.refused == ()
    s.history.execute(C.ApplyCorrections(got.accepted, got.fingerprint, got.file_name))
    assert s.results.outcomes[a900].count_status.value == "counted_corrected"


@pytest.mark.parametrize("how", ["delete", "one_digit", "other_install"])
def test_case_2_signature(tmp_path, setup, how):
    s, grid, a900 = setup
    cell(grid, a900, "Corrected_Zip", "11201")
    mac = None
    if how == "delete":
        cell(grid, a900, "Signature", "")
    elif how == "one_digit":
        sig = cell(grid, a900, "Signature")
        cell(grid, a900, "Signature", sig[:-1] + ("0" if sig[-1] != "0" else "1"))
    else:
        mac = lambda m: hmac.new(bytes(range(32, 64)), m, hashlib.sha256).digest()  # noqa: E731
    got = read_back(s, grid, tmp_path / "r.csv", mac=mac)
    assert got.accepted == () and got.refused[0].sentence_key == "corrections.refused.signature"
    assert copy.get(got.refused[0].sentence_key) == "This row didn't come from this computer's review file."


@pytest.mark.claim("CL-CORR-02")
def test_case_3_original_changed(tmp_path, setup):
    s, grid, a900 = setup
    cell(grid, a900, "Corrected_Zip", "11201")
    cell(grid, a900, "Original_Zip", "10001")
    got = read_back(s, grid, tmp_path / "r.csv")
    assert got.accepted == () and got.refused[0].code == "originals_changed"
    assert copy.get(got.refused[0].sentence_key) == "This row has changed since the review file was made."


@pytest.mark.claim("CL-CORR-03")
def test_case_4_field_not_failing(tmp_path, setup):
    s, grid, a900 = setup
    grid[0].append("Corrected_City")
    for row in grid[1:]:
        row.append("")
    cell(grid, a900, "Corrected_City", "Queens")
    got = read_back(s, grid, tmp_path / "r.csv")
    assert [(r.code, r.column) for r in got.refused] == [("field_not_failing", "City")] and got.accepted == ()
    assert copy.get("corrections.refused.other_column")


def test_case_5_sorted_and_extended(tmp_path, setup):
    s, grid, a900 = setup
    cell(grid, a900, "Corrected_Zip", "11201")
    h = grid[0]
    body = sorted(grid[1:], key=lambda r: r[h.index("Client_ID")], reverse=True)
    extra = [["" for _ in h], ["note row"] + ["" for _ in h[1:]]]
    got = read_back(s, [h] + extra + body, tmp_path / "r.csv")
    assert [c.record_key for c in got.accepted] == [a900]


@pytest.mark.claim("CL-CORR-05")
def test_case_6_not_a_review_file(tmp_path, setup):
    s, grid, a900 = setup
    i = grid[0].index("Signature")
    cut = [r[:i] + r[i + 1:] for r in grid]
    got = read_back(s, cut, tmp_path / "r.csv")
    assert [r.code for r in got.refused] == ["not_a_review_file"] and got.accepted == ()
    assert copy.get("corrections.refused.not_a_review_file")


def test_a_refused_row_never_blocks_another(tmp_path, setup):
    s, grid, a900 = setup
    a500 = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "A500")
    cell(grid, a900, "Corrected_Zip", "11201")
    cell(grid, a500, "Corrected_First_Name", "Eli")
    cell(grid, a500, "Signature", "")
    got = read_back(s, grid, tmp_path / "r.csv")
    assert [c.record_key for c in got.accepted] == [a900] and [r.code for r in got.refused] == ["signature_missing"]
