"""C-27: the old exports changed with upload order. Files are byte-identical whatever the hash seed, and equal apart from the
source letters whatever order files were added in."""
import os
import subprocess
import sys
import textwrap

from tests.conftest import ROOT
from tests.fixtures.outputs.fixture import rows
from tests.fixtures.session import r_fixture
from tests.support.files_run import ack
from tests.support.outputs import read, write
from wholecount.session.runner import process

SCRIPT = textwrap.dedent("""
    import sys, pathlib
    sys.path.insert(0, {root!r})
    from tests.fixtures.outputs.fixture import session
    from tests.support.outputs import write
    s = session(pathlib.Path({tmp!r}), "decided")
    write(s, pathlib.Path({out!r}))
""")


def run(tmp, out, seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    code = SCRIPT.format(root=str(ROOT), tmp=str(tmp), out=str(out))
    p = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stderr


def test_byte_identical_across_hash_seeds(tmp_path):
    run(tmp_path / "a", tmp_path / "oa", 1)
    run(tmp_path / "b", tmp_path / "ob", 99)
    for f in sorted((tmp_path / "oa").iterdir()):
        if f.suffix != ".txt":
            assert f.read_bytes() == (tmp_path / "ob" / f.name).read_bytes(), f.name


def test_reverse_add_order(tmp_path):
    out = {}
    for name, flip in (("fwd", False), ("rev", True)):
        paths = r_fixture.files(tmp_path / name, r=rows())
        s = r_fixture.session(tmp_path / name, paths=list(reversed(paths)) if flip else paths)
        process(s)
        ack(s)
        write(s, tmp_path / f"o{name}")
        out[name] = s
    a, b = out["fwd"], out["rev"]
    assert a.results.identity.master_of_record == b.results.identity.master_of_record and a.counts() == b.counts()
    fa, fb = read(tmp_path / "ofwd" / "Final_Clean_Mapped.csv"), read(tmp_path / "orev" / "Final_Clean_Mapped.csv")
    assert fa == fb
    ua, ub = read(tmp_path / "ofwd" / "Unique_Clients.csv"), read(tmp_path / "orev" / "Unique_Clients.csv")
    strip = lambda rs: [{k: (v if k != "Source_Records" else " ".join(x.split(" :: ", 1)[1] for x in v.split("; "))) for k, v in r.items()}
                        for r in rs]  # noqa: E731
    assert strip(ua) == strip(ub)
