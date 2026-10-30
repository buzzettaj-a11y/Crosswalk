"""The copy registry (H11): unique dotted keys, well-formed unique claim IDs, and strict formatting."""
import re

import pytest

from wholecount import copy
from wholecount.brand import PRODUCT_NAME
from wholecount.copy.registry import CopyError, Entry, load, render

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
CLAIM_RE = re.compile(r"^CL-[A-Z0-9]+(-[A-Z0-9]+)*$")


def test_keys_are_unique_and_lowercase_dotted():
    from tests.conftest import ROOT

    text = (ROOT / "wholecount" / "copy" / "en.toml").read_text(encoding="utf-8")
    headers = re.findall(r"^\[([^\]]+)\]", text, re.M)
    assert len(headers) == len(set(headers))
    keys = [e.key for e in copy.all_entries()]
    assert len(keys) == len(set(keys))
    assert all(KEY_RE.match(k) for k in keys), keys


def test_claim_ids_are_well_formed_and_unique():
    ids = [e.claim for e in copy.all_entries() if e.claim]
    assert ids, "the registry has at least one claim"
    assert all(i.startswith("CL-") and CLAIM_RE.match(i) for i in ids), ids
    assert len(ids) == len(set(ids))


def test_claim_pattern_rejects_bad_ids():
    for bad in ("CL-", "CL-offline-01", "OFFLINE-01", "CL--01", "CL-OFFLINE_01", "CL-OFFLINE-01-"):
        assert not CLAIM_RE.match(bad), bad
    for good in ("CL-OFFLINE-01", "CL-GUIDE-EXAMPLE-01", "CL-A1-2"):
        assert CLAIM_RE.match(good), good


def test_offline_claim_is_registered():
    assert copy.claims() == {"CL-OFFLINE-01": "offline.nothing_leaves"}
    assert copy.get("offline.nothing_leaves") == "Nothing leaves this computer."


def test_ints_get_thousands_separators():
    e = Entry("t.rows", "{rows} rows")
    assert render(e, {"rows": 1234}) == "1,234 rows"
    assert render(e, {"rows": 1234567}) == "1,234,567 rows"


def test_product_is_injected():
    assert copy.get("app.version_line", version="0.1.0") == f"{PRODUCT_NAME} 0.1.0"
    with pytest.raises(CopyError):
        render(Entry("t.p", "{product}"), {"product": "Other"})


def test_missing_or_extra_parameter_raises():
    e = Entry("t.rows", "{rows} rows in {file}")
    with pytest.raises(CopyError):
        render(e, {"rows": 1})
    with pytest.raises(CopyError):
        render(e, {"rows": 1, "file": "a.csv", "extra": 2})
    with pytest.raises(CopyError):
        copy.get("offline.nothing_leaves", rows=1)
    with pytest.raises(CopyError):
        copy.get("no.such_key")


def test_load_reads_nested_tables_with_optional_claims():
    entries = load('[a.b]\ntext = "One."\n\n[a.c.d]\ntext = "Two."\nclaim = "CL-X-01"\n')
    assert entries == {"a.b": Entry("a.b", "One.", None), "a.c.d": Entry("a.c.d", "Two.", "CL-X-01")}
