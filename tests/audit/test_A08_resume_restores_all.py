"""A-08: the old resume lost decisions and previews. Every decision comes back, matched by fingerprint and record key."""

from tests.fixtures.outputs.fixture import districts
from tests.fixtures.session import r_fixture
from tests.support.fake_dpapi import FakeDpapi
from tests.support.session import base, group, rk
from wholecount.engine.corrections import VerifiedCorrection
from wholecount.session import commands as C
from wholecount.session.resume import resume
from wholecount.session.runner import process
from wholecount.session.store import Store, snapshot



def decided(tmp_path):
    s = base(tmp_path / "a", districts=districts(tmp_path))
    s.history.execute(C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0]))
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    s.history.execute(C.AcceptFills([rk(s, "R13")]))
    s.history.execute(C.DecidePair(*s.results.identity.proposals[0].pair, "different"))
    s.history.execute(C.DecideProgramGroup("confirm", ("Housing", "Workforce")))
    corr = [VerifiedCorrection(rk(s, "R11", "Ivy"), (("Zip", "11222"),))]
    s.history.execute(C.ApplyCorrections(corr, "c" * 64, "fix.csv"))
    return s, corr


def restart(tmp_path, s, corr, name, paths):
    fd = FakeDpapi()
    store = Store(tmp_path / "data", fd.protect, fd.unprotect)
    saved = store.load(store.save("x", snapshot(s)))
    s2 = r_fixture.session(tmp_path / name, paths=paths, districts=s.districts)
    plan = resume(s2, saved, paths)
    s2.history.execute(C.ApplyCorrections(corr, "c" * 64, "fix.csv"))
    return s2, plan


def test_every_decision_comes_back(tmp_path):
    s, corr = decided(tmp_path)
    paths = [tmp_path / "a" / "R.csv", tmp_path / "a" / "S.csv"]
    s2, plan = restart(tmp_path, s, corr, "b", paths)
    assert plan.lapsed == 1 and plan.lapsed_list[0][1] == "file_removed"
    assert s2.results.digest() == s.results.digest() and len(s2.decisions) == len(s.decisions)
    process(s2)
    assert s2.results.digest() == s.results.digest()
    s3, plan3 = restart(tmp_path, s, corr, "c", list(reversed(paths)))
    assert s3.results.digest() == s.results.digest()


def test_sorted_file_is_changed_with_the_same_digest(tmp_path):
    s, corr = decided(tmp_path)
    sorted_rows = sorted(r_fixture.r_rows(), key=lambda r: r[2])
    paths = r_fixture.files(tmp_path / "d", r=sorted_rows)
    s2, plan = restart(tmp_path, s, corr, "d2", paths)
    assert plan.changed == ("R.csv",) and plan.restored == ("S.csv",)
    assert s2.results.digest() == s.results.digest()


def test_changed_row_text_lapses_only_its_decision(tmp_path):
    s, corr = decided(tmp_path)
    rs = r_fixture.r_rows()
    r14 = next(i for i, r in enumerate(rs) if r[0] == "R14")
    rs[r14][2] = "Mossy"
    paths = r_fixture.files(tmp_path / "e", r=rs)
    s2, plan = restart(tmp_path, s, corr, "e2", paths)
    reasons = dict(plan.lapsed_list)
    approve = next(d for d in s.decisions if d.kind == "approve")
    assert reasons[approve.decision_id] == "record_gone" and plan.kept == len(s.decisions) - 2
