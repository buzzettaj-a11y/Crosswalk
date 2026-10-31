"""SPEC 5.1 person keys: the vectors, trimming and case, and both fallbacks."""
from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from wholecount.session.keys import person_key
from wholecount.session.secret_store import InstallSecret

S = InstallSecret(TEST_SECRET)


def test_vectors():
    assert person_key(S, "Clinic Export ", client_id=" C-1001 ") == "064ab6000867a82fc1aae7bbbbf3d62558904674cd07672d911107e7ea45d2af"
    assert person_key(S, "Clinic Export", given="ada", surname="sample", dob="1990-04-03") == (
        "1479425de31cd50ffc98c3d015fb5f7ea08fe5c57c8c2981b4f43ee0f12f96c6")
    assert person_key(S, "Clinic Export", given="ada", surname="sample", address_key="45 park ave 10013") == (
        "f8250bc7f0a1e6406e1ad2e301bc7f5b819bc99a0c88dd01b175e0c094b758ac")


def test_system_case_and_spaces_and_client_id_spaces_do_not_matter():
    assert person_key(S, "  CLINIC EXPORT", client_id="C-1001") == person_key(S, "clinic export", client_id=" C-1001 ")


def test_client_id_wins_over_names():
    assert person_key(S, "x", client_id="1", given="a", surname="b", dob="2000-01-01") == person_key(S, "x", client_id="1")


def test_blank_client_id_falls_back():
    assert person_key(S, "x", client_id="  ", given="a", surname="b", dob="2000-01-01") == person_key(
        S, "x", given="a", surname="b", dob="2000-01-01")


def test_dob_slot_stays_empty_in_the_address_fallback():
    with_addr = person_key(S, "x", given="a", surname="b", address_key="1 main st 10001")
    assert with_addr != person_key(S, "x", given="a", surname="b", dob="1 main st 10001")


def test_system_and_secret_matter():
    assert person_key(S, "a", client_id="1") != person_key(S, "b", client_id="1")
    assert person_key(S, "a", client_id="1") != person_key(InstallSecret(OTHER_SECRET), "a", client_id="1")
