"""H9: no decision holds a cell value. Every decision made in the R fixture is scanned for its names, streets, dates and ZIPs."""
from tests.fixtures.session import r_fixture
from tests.support.session import decided
from wholecount.engine.corrections import VerifiedCorrection
from wholecount.session import commands as C


def test_scan(tmp_path):
    s = decided(tmp_path)
    for p in list(s.results.identity.proposals):
        s.history.execute(C.DecidePair(*p.pair, "different"))
    k = next(iter(s.results.rows))
    s.history.execute(C.ApplyCorrections([VerifiedCorrection(k, (("Zip", "10001"),))], "f" * 64))
    text = repr(s.decisions.snapshot()) + repr(s.audit)
    values = {v for row in r_fixture.r_rows() + r_fixture.s_rows() for v in row[1:] if len(v) > 3}
    values -= {"Brooklyn", "Housing", "Youth", "Workforce"}
    values.add("10001")
    for v in values:
        assert v not in text, v
