"""H9: the install secret never appears in a message, a repr or dev output, and the Windows store never writes it in the clear."""
import os
import subprocess
import sys

from tests.conftest import ROOT
from tests.support.fake_dpapi import FakeDpapi
from tests.support.load import load
from tests.support.secrets import TEST_SECRET
from tests.support.files import write_text
from wholecount.engine.progress import RecordingSink, render
from wholecount.session.secret_store import DpapiSecretStore, InstallSecret, get_or_create_secret


def test_not_in_messages_or_reprs(tmp_path):
    sink = RecordingSink()
    r = load([write_text(tmp_path, "a.csv", "Client_ID,First_Name,Last_Name\n1,Ana,Lee\n")], sink=sink)
    hexed = TEST_SECRET.hex()
    texts = [render(m) for m in sink.messages()] + [repr(m) for m in sink.messages()] + [repr(r), repr(InstallSecret(TEST_SECRET))]
    assert not any(hexed in t or repr(TEST_SECRET) in t for t in texts)


def test_windows_store_file_is_not_the_plain_secret(tmp_path):
    d = FakeDpapi()
    s, _ = get_or_create_secret(DpapiSecretStore(tmp_path, d.protect, d.unprotect))
    on_disk = (tmp_path / "key.bin").read_bytes()
    assert s._value not in on_disk


def test_dev_secret_prints_no_secret(tmp_path):
    env = dict(os.environ, WHOLECOUNT_DATA_DIR=str(tmp_path))
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "secret"], cwd=ROOT, capture_output=True, text=True, env=env, timeout=60)
    assert p.returncode == 0, p.stderr
    secret = (tmp_path / "key.bin").read_bytes()
    assert secret.hex() not in p.stdout and secret.hex()[:16] not in p.stdout
    assert p.stdout.splitlines() == ["install_secret_created 1", "install_secret_present 1", "install_secret_bytes 32",
                                     "store_is_dpapi 0", "stored_blob_is_larger_than_secret 0"]
