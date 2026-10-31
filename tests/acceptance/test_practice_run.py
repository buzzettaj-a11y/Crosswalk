"""P-GEO-4: the example data runs by both routes with the sample reference, and everything from it is marked PRACTICE. A
batch of the operator's own files refuses the sample reference, and the guide's example numbers equal this run."""
import csv
import io
import shutil

from tests.acceptance.drive import DATA
from wholecount import copy
from wholecount.copy.guide import example_numbers
from wholecount.engine.geo.backend import preflight, select_backend
from wholecount.engine.outputs.columns import DISTRICT_COLUMNS
from wholecount.session.frame import sample_backend, summary_html

DATA_SUFFIXES = (".csv", ".xlsx", ".json")


def _first_row(path):
    text = path.read_bytes().decode("utf-8-sig")
    return next(csv.reader(io.StringIO(text)))


def test_every_file_name_starts_practice(practice_routes):
    for name in ("fast", "stage"):
        folder = practice_routes[name][2]
        names = [p.name for p in folder.rglob("*") if p.is_file()]
        assert names and all(n.startswith("PRACTICE_") for n in names)


def test_every_data_file_starts_with_a_practice_column(practice_routes):
    for name in ("fast", "stage"):
        for p in practice_routes[name][2].rglob("*.csv"):
            text = p.read_bytes().decode("utf-8-sig")
            rows = list(csv.reader(io.StringIO(text)))
            assert rows[0][0] == "PRACTICE", p.name
            assert all(r[0] == "PRACTICE" for r in rows[1:]), p.name


def test_both_logs_open_with_the_practice_line(practice_routes):
    line = copy.get("log.practice_line")
    for name in ("fast", "stage"):
        for p in practice_routes[name][2].rglob("*_Audit_Log.txt"):
            assert p.read_text(encoding="utf-8").splitlines()[0] == line, p.name


def test_no_map_file_or_district_column(practice_routes):
    for name in ("fast", "stage"):
        folder = practice_routes[name][2]
        assert not [p for p in folder.rglob("*") if "Map_" in p.name]
        for p in folder.rglob("*.csv"):
            assert not set(_first_row(p)) & set(DISTRICT_COLUMNS), p.name


def test_the_printed_page_opens_with_the_practice_line(practice_routes):
    s = practice_routes["fast"][0]
    html = summary_html(s, False)
    body = html.split("<body", 1)[1]
    first_text = [t for t in (x.split(">", 1)[-1].strip() for x in body.split("<")) if t][0]
    assert first_text == copy.get("summary.practice_line")


def test_own_files_refuse_the_sample_reference(tmp_path):
    """The sample file copied into the real reference folder is still the sample, and a batch of the operator's own files
    uses no backend."""
    ref = tmp_path / "reference"
    ref.mkdir()
    shutil.copy(DATA / "sample_reference.csv", ref / "addresses.csv")
    pf = preflight({}, tmp_path, __import__("datetime").date(2026, 10, 30), discover=lambda env: (None, "not_installed"),
                   district_dir=tmp_path / "none")
    assert pf.reference_kind == "sample" and pf.backend_name == "none" and not pf.can_place
    assert select_backend(None, sample_backend(), allow_sample=False).name == "none"
    assert select_backend(None, sample_backend(), allow_sample=True).name == "reference_sample"


def test_no_backend_run_is_not_practice(no_backend_run):
    s, _, folder = no_backend_run
    assert not s.results.practice
    assert not [p for p in folder.rglob("*") if p.name.startswith("PRACTICE_")]


def test_the_guide_example_numbers_equal_this_run(practice_routes):
    for name in ("fast", "stage"):
        s = practice_routes[name][0]
        c, loc = s.results.counts, s.results.counts.locations
        run = {"received": c.received, "counted": c.counted, "not_counted_yet": c.not_counted_yet, "aside": c.set_aside,
               "mapped": loc.mapped, "not_mapped": loc.not_mapped, "goal1": c.goal1.high, "goal2": c.goal2.high}
        assert run == example_numbers()
