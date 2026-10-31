"""P-READ-10: readers take only a local pathlib.Path, and XML parsers never fetch or expand anything."""
import pytest

from tests.support.guarded import ROOT, run_guarded
from wholecount.engine.read.reader import read_path

pytestmark = pytest.mark.claim("CL-OFFLINE-01")

XXE = ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
       "<r><rec><a>&xxe;</a><b>ok</b></rec></r>")
EXTERNAL_DTD = '<?xml version="1.0"?><!DOCTYPE r SYSTEM "http://127.0.0.1:9/x.dtd"><r><rec><a>ok</a></rec></r>'


def test_a_str_path_raises():
    with pytest.raises(TypeError):
        read_path(str(ROOT / "README.md"))


@pytest.mark.parametrize("xml", [XXE, EXTERNAL_DTD], ids=["xxe", "external_dtd"])
def test_xml_entities_and_dtds_load_nothing_under_the_guard(tmp_path, xml):
    p = tmp_path / "a.xml"
    p.write_text(xml, encoding="utf-8")
    r = run_guarded(f"""
        import pathlib
        from wholecount.engine.read.reader import read_path
        rf = read_path(pathlib.Path({str(p)!r}))
        g = rf.grids[0]
        out['header'] = g.fixed_header
        out['rows'] = g.rows
        out['violations'] = violations
    """, install="guard.install_for_app()")
    assert r["violations"] == []
    assert "root:" not in repr(r["rows"])
    assert all(v in ("", "ok") for row in r["rows"] for v in row), r["rows"]
