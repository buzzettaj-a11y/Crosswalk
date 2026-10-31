"""P-GEO-8 (C-10): Process runs end to end on the R and S fixture with the fake, a reference and no backend."""
import pytest

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from wholecount.engine.geo.backend import NoBackend
from wholecount.engine.geo.fake import FakeGeoBackend
from wholecount.session.runner import process


class _FakeOak(FakeGeoBackend):
    pass


@pytest.mark.parametrize("which", ["fake", "reference", "none"])
def test_each_backend(tmp_path, which):
    if which == "fake":
        gaz = tmp_path / "gaz.csv"
        gaz.write_text("house,street,zip,borough,lat,lon,senate,assembly,council,tract,grc\n"
                       + "".join(f"{h},{st},{z},{b},{la},{lo},1,2,3,0001,00\n" for h, st, z, b, la, lo in r_fixture.GAZETTEER))
        backend = FakeGeoBackend(gaz)
    elif which == "reference":
        backend = r_fixture.reference()
    else:
        backend = NoBackend()
    s = r_fixture.session(tmp_path, backend=backend)
    process(s)
    c = s.counts()
    if which == "none":
        assert c.locations.no_geocoder > 0 and c.locations.mapped == 0
    else:
        assert c.locations.high >= 1
    assert (ROOT / "tests").exists()
