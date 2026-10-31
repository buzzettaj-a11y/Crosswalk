"""P-READ-9, H10 and fix plan 4.1: sensitive columns are dropped at load, by name or by values, and leave nothing behind."""
import gc

import pytest

from tests.conftest import ROOT
from tests.support.files import write_text
from tests.support.load import load
from wholecount.engine.read.sensitive import looks_like_ssn_column, sensitive_name, ssn_shaped


@pytest.mark.parametrize("header", ["SSN", "Client SSN", "Social Security Number", "Medicaid ID", "Gender", "Sex", "Race",
                                    "Ethnicity", "Religion", "Diagnosis", "HIV status", "Immigration Status", "client_ssn"])
def test_listed_names(header):
    assert sensitive_name(header)


@pytest.mark.parametrize("header", ["Sexton", "Grace", "Racer", "DOB", "Date of Birth", "Address", "Social Club", "SSNumber"])
def test_whole_words_only_and_dob_not_listed(header):
    assert not sensitive_name(header)


@pytest.mark.parametrize("value", ["078-05-1120", "219099999", "123-45-6789"])
def test_ssn_shaped(value):
    assert ssn_shaped(value)


@pytest.mark.parametrize("value", ["000123456", "666451234", "900123456", "123-45-678", "2125551234", "12345678", "219009999",
                                   "219090000", "abc-de-fghi"])
def test_not_ssn_shaped(value):
    assert not ssn_shaped(value)


def test_half_rule():
    assert looks_like_ssn_column(["078-05-1120", "219099999", "x"])
    assert not looks_like_ssn_column(["078-05-1120", "x"])
    assert not looks_like_ssn_column(["", ""])


def test_drop_by_name_and_keep(tmp_path):
    p = write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name,SSN,Gender,DOB\n1,Ana,Lee,078-05-1120,F,1990-01-01\n")
    t = load([p]).tables[0]
    assert t.headers == ["Client_ID", "First_Name", "Last_Name", "DOB"]
    assert t.sensitive_dropped == ["SSN", "Gender"] and t.rows == [["1", "Ana", "Lee", "1990-01-01"]]
    t = load([p], keep=frozenset({"Gender"})).tables[0]
    assert t.headers == ["Client_ID", "First_Name", "Last_Name", "Gender", "DOB"] and t.sensitive_dropped == ["SSN"]


def test_drop_by_values_whatever_the_name(tmp_path):
    p = write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name,Notes\n1,Ana,Lee,078-05-1120\n2,Ben,Cho,219099999\n3,Cy,Ra,x\n")
    t = load([p]).tables[0]
    assert "Notes" not in t.headers and t.sensitive_dropped == ["Notes"] and t.sensitive_by_values == 1


def test_exactly_half_is_kept(tmp_path):
    p = write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name,Notes\n1,Ana,Lee,078-05-1120\n2,Ben,Cho,ok\n")
    assert "Notes" in load([p]).tables[0].headers


def test_keys_are_the_same_whether_a_column_is_kept_or_dropped(tmp_path):
    p = write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name,SSN\n1,Ana,Lee,078-05-1120\n")
    assert load([p]).tables[0].record_keys == load([p], keep=frozenset({"SSN"})).tables[0].record_keys


def test_audit_fixture_still_drops_ssn():
    t = load([ROOT / "tests" / "data" / "audit" / "ssn_unmapped.csv"]).tables[0]
    assert "SSN" in t.sensitive_dropped and "SSN" not in t.headers


def _reachable_strings(prefix):
    gc.collect()
    found = 0
    for o in gc.get_objects():
        items = ()
        if isinstance(o, (list, tuple, set, frozenset)):
            items = o
        elif isinstance(o, dict):
            items = list(o.keys()) + list(o.values())
        elif hasattr(o, "__dict__") and not isinstance(o, type):
            try:
                items = list(vars(o).values())
            except TypeError:
                items = ()
        for x in items:
            if isinstance(x, (str, bytes)) and prefix in (x if isinstance(x, str) else x.decode("latin-1")):
                found += 1
    return found


def test_no_dropped_value_stays_reachable(tmp_path):
    marker = "".join(["Q", "Z", "S", "N"])
    lines = ["Client_ID,First_Name,Last_Name,SSN"] + [f"{i},Ana,Lee,{marker}{i:05d}" for i in range(50)]
    p = tmp_path / "a.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    del lines
    result = load([p])
    assert result.tables[0].sensitive_dropped == ["SSN"]
    assert _reachable_strings(marker) == 0


def test_the_scan_finds_values_in_a_kept_column(tmp_path):
    """Negative control: the same scan finds the values when the column is kept on purpose."""
    marker = "".join(["Q", "Z", "K", "P"])
    lines = ["Client_ID,First_Name,Last_Name,SSN"] + [f"{i},Ana,Lee,{marker}{i:05d}" for i in range(50)]
    p = tmp_path / "a.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    del lines
    result = load([p], keep=frozenset({"SSN"}))
    assert _reachable_strings(marker) >= 50
    del result
