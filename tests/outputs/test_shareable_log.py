"""The shareable log: the second keyed hash, the same events line for line, reviewer names kept, and UNDO lines present."""
from tests.fixtures.outputs.fixture import session
from tests.support.outputs import write
from tests.support.session import rk
from wholecount.engine.outputs.review_file import share_key
from wholecount.session import commands as C


def test_shareable(tmp_path):
    s = session(tmp_path, "decided")
    s.history.execute(C.SetAsideRows([rk(s, "00123")], "test_record"))
    s.history.undo()
    write(s, tmp_path / "out")
    internal = (tmp_path / "out" / "Internal_Audit_Log.txt").read_text(encoding="utf-8").splitlines()
    share = (tmp_path / "out" / "Shareable_Audit_Log.txt").read_text(encoding="utf-8").splitlines()
    ev_i = [l.split(" ")[1] for l in internal if l[:2] == "20"]
    ev_s = [l.split(" ")[1] for l in share if l[:2] == "20"]
    assert ev_i == ev_s and "UNDO" in ev_s
    r14 = rk(s, "R14")
    assert any(share_key(s.secret.mac, r14) in l for l in share) and not any(r14 in l for l in share)
    assert any('reviewer="Joe"' in l for l in share)
