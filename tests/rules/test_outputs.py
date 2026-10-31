"""The output files, printable summary and receipt (SPEC 9.1, 9.3, 9.4): OUT-1 to OUT-14, SUM-1 to SUM-3."""
import pathlib

import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.outputs import header, read, write
from wholecount import copy
from wholecount.engine.outputs.columns import FileId, chip_columns
from wholecount.engine.outputs.folders import folder_warning
from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html
from wholecount.engine.outputs.view import ExportSettings
from wholecount.engine.outputs.writer import FolderNeedsConfirm, WouldOverwrite, write_outputs
from wholecount.session.export import build_view, download


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    d = tmp_path_factory.mktemp("base")
    s = session(d)
    receipt = write(s, d / "out")
    return s, d / "out", receipt


def test_OUT_1_chips_equal_headers(base):
    s, out, _ = base
    view = build_view(s)
    for f in (FileId.FINAL_CLEAN_MAPPED, FileId.UNIQUE_CLIENTS, FileId.SET_ASIDE_RECORDS, FileId.MANUAL_REVIEW_NEEDED):
        assert header(out / f"{f.value}.csv") == chip_columns(f, view, ExportSettings())


def test_OUT_2_final_clean_mapped(base):
    s, out, _ = base
    rows = read(out / "Final_Clean_Mapped.csv")
    assert len(rows) == 13
    cols = header(out / "Final_Clean_Mapped.csv")
    assert cols[-5:] == ["Source_File", "Source_Row", "Record_Key", "Duplicate_In_File", "Possible_Duplicate_Of"]
    assert "Latitude" not in cols and "Senate_District" in cols
    ada = next(r for r in rows if r["Client_ID"] == "00123")
    assert ada["Source_File"] == "R.csv" and ada["Source_Row"] == "2" and ada["Count_Status"] == "Counted, passed every count check"
    gus = [r for r in rows if r["Client_ID"] == "R07"]
    assert all(r["Duplicate_In_File"] == "Yes" for r in gus) and gus[0]["Possible_Duplicate_Of"] == gus[1]["Record_Key"]
    assert next(r for r in rows if r["Client_ID"] == "R13")["Location_Status"].startswith("Not mapped: Address problem")
    assert not any("passed every check" == r["Count_Status"] for r in rows)


def test_OUT_3_and_4_people_files(base):
    s, out, _ = base
    u, p = read(out / "Unique_Clients.csv"), read(out / "Unique_Clients_By_Program.csv")
    assert len(u) == s.counts().goal1.high == 11 and len(p) == s.counts().goal2.high == 11
    ada = next(r for r in u if r["First_Name"] == "Ada")
    assert ada["Systems"] == "R; S" and ada["Source_Records"].count("::") == 4 and ada["Match_Confidence"] == "Certain"


def test_OUT_5_and_6_review_and_set_aside(base):
    s, out, _ = base
    assert len(read(out / "Manual_Review_Needed.csv")) == 8
    (aside,) = read(out / "Set_Aside_Records.csv")
    assert aside["Reason"] == "Summary row" and aside["Kept_Record_Key"] == ""


def test_OUT_7_map_counts_blank_small_cells(base):
    s, out, _ = base
    rows = read(out / "Map_Counts.csv")
    assert rows and all(r["Count"] == "fewer than 11" for r in rows)
    assert set(rows[0]) == {"Program", "District_Type", "District", "Count"}


def test_OUT_8_map_points_off_by_default(base):
    s, out, _ = base
    assert not (out / "Map_Points.csv").exists()


def test_OUT_9_quality_report(base):
    s, out, _ = base
    rows = read(out / "Data_Quality_Report.csv")
    assert [r["Source_File"] for r in rows] == ["R.csv", "S.csv"]
    assert rows[0]["Rows_Received"] == "15" and rows[0]["Problem_name_missing"] == "1" and rows[0]["Encoding"]
    assert "Counted_Not_Mapped" in rows[0]


def test_OUT_10_practice(tmp_path):
    s = session(tmp_path, backend=_sample(), allow_sample=True)
    receipt = write(s, tmp_path / "out")
    names = sorted(pathlib.Path(f.path).name for f in receipt.files)
    assert all(n.startswith("PRACTICE_") for n in names) and len(names) == 8
    assert header(tmp_path / "out" / "PRACTICE_Final_Clean_Mapped.csv")[0] == "PRACTICE"
    assert "Senate_District" not in header(tmp_path / "out" / "PRACTICE_Final_Clean_Mapped.csv")
    assert (tmp_path / "out" / "PRACTICE_Internal_Audit_Log.txt").read_text().splitlines()[0] == copy.get("log.practice_line")


def _sample():
    from tests.fixtures.session import r_fixture
    from wholecount.engine.geo.reference import ReferenceBackend
    text = "house_number,street,zip,borough,latitude,longitude\n" + "".join(",".join(map(str, g)) + "\n" for g in r_fixture.GAZETTEER)
    return ReferenceBackend.from_text(text, is_sample=True)


def test_OUT_11_row_order(base):
    s, out, _ = base
    rows = read(out / "Final_Clean_Mapped.csv")
    keys = [(r["Source_File"], int(r["Source_Row"])) for r in rows]
    assert keys == sorted(keys)


def test_OUT_12_formats(tmp_path):
    s = session(tmp_path)
    write(s, tmp_path / "x", formats={"Final_Clean_Mapped": "xlsx", "Unique_Clients": "json"})
    raw = (tmp_path / "x" / "Data_Quality_Report.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw
    assert all(isinstance(v, str) for r in read(tmp_path / "x" / "Unique_Clients.json") for v in r.values())
    assert any(r["Client_ID"] == "00123" for r in read(tmp_path / "x" / "Final_Clean_Mapped.xlsx"))


def test_OUT_13_gate_and_no_overwrite(tmp_path):
    s = session(tmp_path)
    write(s, tmp_path / "o")
    before = sorted(p.name for p in (tmp_path / "o").iterdir())
    with pytest.raises(WouldOverwrite):
        download(s, tmp_path / "o", ExportSettings())
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == before


def test_OUT_14_folders(tmp_path):
    assert folder_warning(r"C:\Users\x\OneDrive - Org\y", {}) == "onedrive"
    view = build_view(session(tmp_path))
    with pytest.raises(FolderNeedsConfirm):
        write_outputs(view, tmp_path / "Dropbox", ExportSettings(), lambda: __import__("datetime").datetime(2026, 1, 1))


@pytest.mark.claim("CL-OUT-04")
@pytest.mark.claim("CL-OUT-05")
def test_SUM_1_and_2_summary(base):
    s, out, _ = base
    view = build_view(s)
    plain = render_summary_html(build_summary(view, False))
    named = render_summary_html(build_summary(view, True))
    assert "Counts only." in plain and "R.csv" not in plain and "<script" not in plain and "http" not in plain
    assert "Counts and file names only." in named and "R.csv" in named
    assert "M-" not in plain and "00123" not in plain and "9 to 11" in plain


@pytest.mark.claim("CL-OUT-06")
@pytest.mark.claim("CL-OUT-08")
def test_SUM_3_receipt(base):
    from wholecount.engine.outputs.receipt import receipt_text
    s, out, receipt = base
    assert sorted(pathlib.Path(f.path).name for f in receipt.files) == sorted(p.name for p in out.iterdir())
    text = receipt_text(receipt)
    assert copy.get("receipt.nothing_else") in text and "possible same-person pairs were open" in text
