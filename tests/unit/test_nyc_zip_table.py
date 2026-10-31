"""P-STD-3: the NYC ZIP table. An explicit list from cited sources, with the ZIPs the spec names."""
import csv
import io
import subprocess
import sys
from importlib import resources

from tests.conftest import ROOT
from wholecount.engine.geo.zips import borough_for_zip, is_nyc_zip, nyc_zips

TEXT = resources.files("wholecount.engine.geo").joinpath("data/nyc_zips.csv").read_text(encoding="utf-8")
ROWS = list(csv.DictReader(io.StringIO(TEXT)))
SPEC_NAMED = {"11004", "11005", "10463", *(str(n) for n in range(11690, 11698))}


def test_required_zips():
    for z in ("11004", "11005", *(str(n) for n in range(11690, 11698))):
        assert borough_for_zip(z) == "Queens", z
    assert borough_for_zip("10463") == "Bronx"


def test_absent_zips():
    for z in ("11001", "11580", "07030", "12345", "99999", "00000"):
        assert not is_nyc_zip(z), z


def test_shape():
    zips = [r["zip"] for r in ROWS]
    assert zips == sorted(zips) and len(zips) == len(set(zips)) and len(zips) > 150
    assert all(len(z) == 5 and z.isascii() and z.isdigit() for z in zips)
    assert {r["borough"] for r in ROWS} == {"New York", "Brooklyn", "Queens", "Bronx", "Staten Island"}
    assert all(r["source"] for r in ROWS)
    assert nyc_zips()["11201"] == "Brooklyn"


def test_zips_cited_to_the_spec_are_ones_the_spec_names():
    assert {r["zip"] for r in ROWS if r["source"] == "SPEC.md P-STD-3"} <= SPEC_NAMED


def test_the_table_matches_its_sources():
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "make_zip_table.py"), "--check"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "table_matches 1" in p.stdout
