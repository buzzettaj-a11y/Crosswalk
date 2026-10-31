"""A crosswalk made under another install secret (M13 XW-3)."""
import pytest

from tests.support import crosswalk as X
from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from wholecount.engine.crosswalk.schema import CrosswalkOrphaned
from wholecount.engine.crosswalk.store import CrosswalkStore
from wholecount.engine.identity import master_id
from wholecount.session import crosswalk
from wholecount.session.backup import BackupSecret, RestoreSecret
from wholecount.session.secret_store import FileSecretStore, InstallSecret

PASS = "correct horse battery staple"


def test_orphaned_then_restored(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    BackupSecret(PASS, PASS, tmp_path / "secret.wcb").run(s)
    with pytest.raises(CrosswalkOrphaned):
        CrosswalkStore.open(xw, InstallSecret(OTHER_SECRET).mac)
    before = xw.read_bytes()
    o = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], day=1)
    o.secret = InstallSecret(OTHER_SECRET)
    assert crosswalk.state(o) == "orphaned"
    X.run(o)
    assert o.results.crosswalk is None and o.results.counts.matched_from_earlier is None
    assert all(m == master_id(k) for k, m in o.results.identity.master_of.items() if len(o.results.identity.groups[m]) == 1)
    X.decide_truth(o)
    X.download(o, tmp_path / "o2")
    assert xw.read_bytes() == before
    store = FileSecretStore(tmp_path / "key")
    store.save(OTHER_SECRET)
    assert RestoreSecret(tmp_path / "secret.wcb", PASS, "replace").run(o, store).restored
    assert crosswalk.state(o) == "on" and store.load() == TEST_SECRET
    X.run(o)
    assert o.results.crosswalk is not None and o.results.counts.matched_from_earlier == 0
