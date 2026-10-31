"""select_backend (P-GEO-1 to P-GEO-4): Geosupport, then a real reference, then nothing. Never the fake, and a sample only when
allowed."""
import ast

from tests.conftest import ROOT
from tests.support.geo import SAMPLE, fake, ref_b17
from wholecount.engine.geo.backend import NoBackend, select_backend
from wholecount.engine.geo.geosupport import GeosupportBackend
from wholecount.engine.geo.reference import ReferenceBackend

GEO = GeosupportBackend(object(), KeyError, "25C")


def test_geosupport_first():
    assert select_backend(GEO, ref_b17()) is GEO


def test_real_reference_second():
    ref = ref_b17()
    assert select_backend(None, ref) is ref


def test_nothing_gives_no_backend():
    assert isinstance(select_backend(None, None), NoBackend)


def test_sample_refused_unless_allowed():
    sample = ReferenceBackend.from_path(SAMPLE)
    assert isinstance(select_backend(None, sample), NoBackend)
    assert select_backend(None, sample, allow_sample=True) is sample
    assert select_backend(GEO, sample, allow_sample=True) is GEO


def test_fake_never_selected():
    assert isinstance(select_backend(fake(), None), NoBackend)
    assert isinstance(select_backend(None, fake(), allow_sample=True), NoBackend)


def test_no_fake_import_in_package():
    """The fake backend is for tests and wholecount.dev only."""
    bad = []
    for p in sorted((ROOT / "wholecount").rglob("*.py")):
        if p.name in ("fake.py", "dev.py"):
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            names = []
            if isinstance(n, ast.ImportFrom):
                names = [n.module or ""] + [f"{n.module}.{a.name}" for a in n.names]
            elif isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            if any(x.endswith("geo.fake") for x in names):
                bad.append(p.relative_to(ROOT).as_posix())
    assert bad == []
