"""Load files with the test secret."""
import pathlib

from tests.support.secrets import TEST_SECRET
from wholecount.engine.progress import NullSink
from wholecount.session.loader import load_files
from wholecount.session.secret_store import InstallSecret


def load(paths, keep=frozenset(), secret=TEST_SECRET, sink=None):
    return load_files([pathlib.Path(p) for p in paths], sink or NullSink(), InstallSecret(secret), keep)
