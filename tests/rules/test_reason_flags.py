"""P-VAL-3: every decision reason has exactly one flag and a problems.toml entry with four keys. Notes have no flag."""
import tomllib
from importlib import resources

import pytest

from wholecount.engine import reasons

PROBLEMS = tomllib.loads(resources.files("wholecount.copy").joinpath("problems.toml").read_text(encoding="utf-8"))


def test_every_decision_reason_has_one_flag_and_an_entry():
    for r in reasons.all_reasons().values():
        if r.severity == "decision":
            assert r.flag in reasons.FLAGS, r.id
            assert set(PROBLEMS[r.id]) == {"title", "means", "check", "excel"}, r.id
        else:
            assert r.flag is None and r.id not in PROBLEMS, r.id


def test_every_problems_entry_is_a_decision_reason():
    for code in PROBLEMS:
        assert reasons.get(code).severity == "decision"


def test_tidy_up_flags():
    assert reasons.get("address_extra_text").flag == "location"
    assert reasons.get("name_order_unclear").flag == "soft" and reasons.get("name_extra_tokens").flag == "soft"
    assert not any(r.flag == "holds_count" for r in reasons.all_reasons().values() if r.id in (
        "address_extra_text", "name_order_unclear", "name_extra_tokens"))


def test_register_refuses_bad_flags():
    with pytest.raises(ValueError):
        reasons.register("x_test", "decision")
    with pytest.raises(ValueError):
        reasons.register("x_test", "note", "soft")
