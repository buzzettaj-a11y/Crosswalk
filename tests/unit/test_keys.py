"""SPEC 5.1 keys: the known-answer vectors from the milestone, and the rules around them."""
import pytest

from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from wholecount.session import keys
from wholecount.session.secret_store import InstallSecret

S = InstallSecret(TEST_SECRET)
ROW = ["Ada Sample", "125 Worth St Apt 4B New York NY 10013"]
TK = "clinic_export_csv :: data :: 3380a5d7"


def test_vectors():
    assert keys.header_signature(["Name", "Full_Address"]) == "3380a5d7"
    assert keys.table_key("clinic_export_csv", None, "3380a5d7") == TK
    assert keys.record_keys(S, TK, [ROW, ROW]) == ["7533705e667f8cf12288", "93babd9489a6553c3676"]
    assert keys.record_keys(S, "clinic_export_csv~a1b2c3 :: data :: 3380a5d7", [ROW]) == ["0d61d191dda29d77ca6f"]
    assert keys.record_keys(InstallSecret(OTHER_SECRET), TK, [ROW]) == ["4a69e20c55510cc8bfa2"]


def test_occurrences_count_exact_duplicates_in_order():
    a, b = ["A", "1"], ["B", "2"]
    ks = keys.record_keys(S, TK, [a, b, a, a])
    assert len(set(ks)) == 4
    assert keys.record_keys(S, TK, [a])[0] == ks[0] and keys.record_keys(S, TK, [b])[0] == ks[1]


def test_a_changed_cell_changes_the_key():
    assert keys.record_keys(S, TK, [["A", "1"]]) != keys.record_keys(S, TK, [["A", "2"]])


def test_key_is_hex_of_20():
    k = keys.record_keys(S, TK, [ROW])[0]
    assert len(k) == 20 and int(k, 16) >= 0


@pytest.mark.parametrize("name,norm", [
    ("Clinic Export.csv", "clinic_export_csv"), ("Clinic Export (Q3).csv", "clinic_export_q3_csv"),
    ("C:\\x\\A  B.xlsx", "a_b_xlsx"), ("/home/x/clinic_export.csv", "clinic_export_csv"), ("--Odd--Name--.TSV", "odd_name_tsv"),
])
def test_normalize_file_name(name, norm):
    assert keys.normalize_file_name(name) == norm


def test_file_keys_suffix_and_duplicates():
    fa, fb = "a1b2c3" + "0" * 58, "ffeedd" + "1" * 58
    out = keys.file_keys([("Clinic Export.csv", fa), ("clinic export.csv", fb), ("Clinic Export.csv", fa), ("Other.csv", fa)])
    assert out == ["clinic_export_csv", "clinic_export_csv~ffeedd", None, "other_csv"]


def test_two_tables_with_one_key_get_ordinals():
    assert keys.table_key("f_csv", "Sheet1", "abcd1234", 2) == "f_csv :: Sheet1 #2 :: abcd1234"
    assert keys.table_key("f_csv", None, "abcd1234", 3) == "f_csv :: data #3 :: abcd1234"
