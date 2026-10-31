"""The guide's own factual sentences (M15)."""
import pytest


@pytest.mark.claim("CL-GUIDE-TYPES-01")
def test_it_reads_the_five_file_types():
    from tests.support.example_session import DATA, NAMES
    from wholecount.engine.read.reader import read_path

    exts = {n.rsplit(".", 1)[1] for n in NAMES}
    assert exts == {"csv", "tsv", "xlsx", "json", "xml"}
    assert all(read_path(DATA / n).grids for n in NAMES)


@pytest.mark.claim("CL-GUIDE-NOGEO-01")
def test_without_a_geocoder_rows_are_checked_counted_and_not_placed(tmp_path):
    from tests.support.example_session import example_session

    s = example_session(tmp_path, practice=False)
    c = s.results.counts
    assert c.counted > 0 and c.locations.mapped == 0
    assert s.results.balance.total("received") == c.counted + c.not_counted_yet + c.set_aside
