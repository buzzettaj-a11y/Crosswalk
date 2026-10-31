"""The two audit logs (SPEC 9.2): AUD-1 to AUD-7."""
import pytest

from tests.fixtures.outputs.fixture import VALUES, session
from tests.support.outputs import write
from tests.support.session import rk
from wholecount import copy
from wholecount.engine.outputs.audit_entry import entry
from wholecount.engine.outputs.audit_text import AuditRenderError, render_line
from wholecount.session import commands as C


def logs(s, out):
    write(s, out)
    return (out / "Internal_Audit_Log.txt").read_text(encoding="utf-8"), (out / "Shareable_Audit_Log.txt").read_text(encoding="utf-8")


def test_AUD_1_append_only_with_undo(tmp_path):
    s = session(tmp_path, "decided")
    n = len(s.audit_log)
    s.history.execute(C.SetAsideRows([rk(s, "00123")], "test_record"))
    s.history.undo()
    assert len(s.audit_log) == n + 2 and s.audit_log[-1][1].code == "UNDO" and s.audit_log[-1][1].get("decision_id")


def test_AUD_2_events(tmp_path):
    s = session(tmp_path, "decided")
    internal, _ = logs(s, tmp_path / "o")
    for code in ("FILE_ADDED", "TABLE_INCLUDED", "DECISION", "AUTO_JOIN", "RUN", "FILL"):
        assert f" {code} " in internal, code
    with pytest.raises(AuditRenderError):
        render_line("2026-01-01T00:00:00Z", entry("RUN", count=1, record_key="abc"))


@pytest.mark.claim("CL-LOG-01")
def test_AUD_3_internal_header_legend_and_reviewer_table(tmp_path):
    internal, _ = logs(session(tmp_path, "decided"), tmp_path / "o")
    lines = internal.splitlines()
    assert lines[0] == copy.get("log.internal_first_line")
    assert "SOURCE A = R.csv" in lines and copy.get("log.reviewer_table") in lines and lines[-1].startswith("Joe: ")


@pytest.mark.claim("CL-LOG-02")
def test_AUD_4_shareable(tmp_path):
    s = session(tmp_path, "decided")
    internal, share = logs(s, tmp_path / "o")
    assert share.splitlines()[0] == copy.get("log.shareable_first_line")
    assert "R.csv" not in share and "SOURCE" not in share and "fingerprint" not in share and "row_number" not in share
    assert rk(s, "R14") not in share and rk(s, "R14") in internal
    assert 'reviewer="Joe"' in share
    assert len([l for l in internal.splitlines() if l[:4] == "2026"]) == len([l for l in share.splitlines() if l[:4] == "2026"])


def test_AUD_5_no_cap(tmp_path):
    s = session(tmp_path)
    keys = [k for k, o in s.results.outcomes.items() if o.set_aside_reason is None][:10]
    s.history.execute(C.SetAsideRows(keys, "test_record"))
    s.history.execute(C.AcknowledgeLowConfidence())
    internal, _ = logs(s, tmp_path / "o")
    assert sum(1 for l in internal.splitlines() if " DECISION " in l) == 10 and "more" not in internal


def test_AUD_6_no_values(tmp_path):
    internal, share = logs(session(tmp_path, "decided"), tmp_path / "o")
    for v in VALUES + ["00123"]:
        assert v not in internal and v not in share, v


def test_AUD_7_resume_starts_with_resume(tmp_path):
    from tests.support.fake_dpapi import FakeDpapi
    from tests.fixtures.outputs.fixture import rows
    from tests.fixtures.session import r_fixture
    from wholecount.session.resume import resume
    from wholecount.session.store import Store, snapshot

    s = session(tmp_path, "decided")
    fd = FakeDpapi()
    store = Store(tmp_path / "data", fd.protect, fd.unprotect)
    saved = store.load(store.save("x", snapshot(s)))
    s2 = r_fixture.session(tmp_path / "in", paths=r_fixture.files(tmp_path / "in", r=rows()))
    resume(s2, saved, [tmp_path / "in" / "R.csv", tmp_path / "in" / "S.csv"])
    assert s2.audit_log[0][1].code == "RESUME"
    assert len(s2.decisions) == len(s.decisions)
