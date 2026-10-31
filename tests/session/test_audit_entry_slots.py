"""CMD-4: an audit entry takes typed slots only, and a KeyedHash has no public constructor."""
import pytest

from wholecount.engine.outputs.audit_entry import AuditSlotError, KeyedHash, entry


def test_slots_only():
    with pytest.raises(AuditSlotError):
        entry("APPROVE", name="Ada")
    with pytest.raises(AuditSlotError):
        entry("APPROVE", count="3")
    with pytest.raises(AuditSlotError):
        entry("APPROVE", file_name="clinic.csv")
    with pytest.raises(AuditSlotError):
        entry("SET_ASIDE", note="x" * 121)
    with pytest.raises(AuditSlotError):
        entry("APPROVE", decision_id="Ada Lee")
    with pytest.raises(AuditSlotError):
        entry("CORRECTION", old_hash="11201")
    e = entry("DOWNLOAD", file_name="out.xlsx", count=3)
    assert e.get("file_name") == ["out.xlsx"]


def test_keyed_hash_has_no_public_constructor():
    with pytest.raises(TypeError):
        KeyedHash(None, "0" * 16)
    with pytest.raises(TypeError):
        KeyedHash()
