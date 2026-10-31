"""H11: each copies and identity sentence states what the engine does."""
import pytest

from tests.fixtures.people.builders import crow, prow, to_person
from wholecount import copy
from wholecount.engine.identity import EVIDENCE_CODES, REASONS, load_settings, resolve, score_pair

W = load_settings()["weights"]


def ev(a, b, rare=False):
    sc = score_pair(a, b, rare, W)
    return set(sc.evidence), set(sc.cautions)


def p(first="Ana", last="Perez", dob="1990-05-06", street="7 Elm St", zip5="11201", key="a", system="A", cid=""):
    return prow(key, system, cid or key, first, last, dob, street, zip5)


def test_every_code_and_reason_has_a_sentence():
    for c in EVIDENCE_CODES:
        assert copy.get(f"people.evidence.{c}")
    for r in REASONS:
        assert copy.get(f"people.join.{r}")


@pytest.mark.claim("CL-ID-EV-01")
def test_dob_exact():
    assert "dob_exact" in ev(p(), p(key="b"))[0]


@pytest.mark.claim("CL-ID-EV-02")
def test_dob_swapped():
    assert "dob_swapped" in ev(p(), p(dob="1990-06-05", key="b"))[0]


@pytest.mark.claim("CL-ID-EV-03")
def test_dob_one_digit():
    assert "dob_one_digit" in ev(p(), p(dob="1990-05-07", key="b"))[0]


@pytest.mark.claim("CL-ID-EV-04")
def test_dob_differs():
    assert "dob_differs" in ev(p(), p(dob="1955-12-25", key="b"))[0]


@pytest.mark.claim("CL-ID-EV-05")
def test_surname_exact():
    assert "surname_exact" in ev(p(last="Pérez"), p(key="b"))[0]


@pytest.mark.claim("CL-ID-EV-06")
def test_surname_part():
    assert "surname_part" in ev(p(last="Perez Soto"), p(key="b"))[0]


@pytest.mark.claim("CL-ID-EV-07")
def test_names_swapped():
    assert "names_swapped" in ev(p(first="Wei", last="Li"), p(first="Li", last="Wei", key="b"))[0]


@pytest.mark.claim("CL-ID-EV-08")
def test_given_exact():
    assert "given_exact" in ev(p(), p(key="b"))[0]


@pytest.mark.claim("CL-ID-EV-09")
def test_given_nickname():
    assert "given_nickname" in ev(p(first="Bob"), p(first="Robert", key="b"))[0]
    assert "Bob and Robert" in copy.get("people.evidence.given_nickname")


@pytest.mark.claim("CL-ID-EV-10")
def test_given_initial():
    assert "given_initial" in ev(p(first="A"), p(key="b"))[0]


@pytest.mark.claim("CL-ID-EV-12")
def test_zip_only():
    assert "zip_only" in ev(p(), p(street="9 Oak Ave", key="b"))[0]


@pytest.mark.claim("CL-ID-EV-13")
@pytest.mark.claim("CL-ID-JOIN-01")
def test_same_system_id():
    rows = [crow("e1", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", "Housing"),
            crow("e2", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", "Youth")]
    (j,) = resolve([to_person(c) for c in rows]).auto_joins
    assert j.reason == "same_system_id" and [e.code for e in j.evidence] == ["same_system_id"]


@pytest.mark.claim("CL-ID-EV-15")
def test_suffix_differs_is_a_caution_with_no_points():
    a, b = p(last="Diaz"), p(last="Diaz Jr", key="b")
    evidence, cautions = ev(a, b)
    assert "suffix_differs" in cautions and "suffix_differs" not in evidence
    assert score_pair(a, b, False, W).points == score_pair(a, p(last="Diaz", key="b"), False, W).points
