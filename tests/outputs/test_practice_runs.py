"""OUT-10 (P-GEO-4, SPEC 9.1): a practice run marks every file and leaves the maps and district columns out."""
import pathlib

import pytest

from tests.fixtures.outputs.fixture import session
from tests.fixtures.session import r_fixture
from tests.support.outputs import header, write
from wholecount import copy
from wholecount.engine.geo.reference import ReferenceBackend
from wholecount.engine.outputs.receipt import receipt_text
from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
from wholecount.session.export import build_view


def sample():
    text = "house_number,street,zip,borough,latitude,longitude\n" + "".join(",".join(map(str, g)) + "\n" for g in r_fixture.GAZETTEER)
    return ReferenceBackend.from_text(text, is_sample=True)


@pytest.mark.claim("CL-OUT-09")
@pytest.mark.claim("CL-OUT-03")
@pytest.mark.claim("CL-LOG-03")
def test_practice(tmp_path):
    s = session(tmp_path, backend=sample(), allow_sample=True)
    receipt = write(s, tmp_path / "out")
    names = sorted(pathlib.Path(f.path).name for f in receipt.files)
    assert len(names) == 8 and all(n.startswith("PRACTICE_") for n in names)
    assert not any("Map_" in n for n in names)
    for n in names:
        if n.endswith(".csv"):
            assert header(tmp_path / "out" / n)[0] == "PRACTICE"
        else:
            assert (tmp_path / "out" / n).read_text(encoding="utf-8").splitlines()[0] == copy.get("log.practice_line")
    assert copy.get("outputs.practice.no_maps") in receipt_text(receipt)
    assert copy.get("summary.practice_line") in render_summary_html(build_summary(build_view(s), False))


def test_same_session_as_a_real_run(tmp_path):
    s = session(tmp_path)
    receipt = write(s, tmp_path / "out")
    assert len(receipt.files) == 9 and "Senate_District" in header(tmp_path / "out" / "Final_Clean_Mapped.csv")
