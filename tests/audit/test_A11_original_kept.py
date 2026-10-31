"""A-11 (Medium): "the value as entered stays on the row" was false when the engine overwrote City."""
import csv

from tests.conftest import ROOT
from tests.support.std import ids, row_input, std, TODAY
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.model import audit_events
from wholecount.engine.standardize.rows import TableOptions, standardize_row

FIXTURE = ROOT / "docs" / "audit" / "A-fixtures" / "misplaced.csv"


def rows():
    out = []
    for rec in csv.DictReader(FIXTURE.open(encoding="utf-8")):
        out.append(standardize_row(row_input(rec["Client_ID"], **{k: v for k, v in rec.items()}), default_schema(), TableOptions(), TODAY))
    return out


def test_A11_every_row_is_counted_and_keeps_what_was_entered():
    rs = rows()
    assert all(r.count_status.counted for r in rs)
    by = {r.record_key: r for r in rs}
    assert ids(by["M001"]) == ["city_not_recognized"] and by["M001"].values["City"].suggestions == ("Brooklyn",)
    assert ids(by["M002"]) == ["city_not_recognized"] and by["M002"].value("City") == "742 Evergreen Terrace"
    assert ids(by["M003"]) == ["state_not_recognized"]
    assert ids(by["M004"]) == ["zip_not_valid"]
    assert ids(by["M005"]) == [] and by["M005"].location.kind == "to_place"
    for rec, r in zip(csv.DictReader(FIXTURE.open(encoding="utf-8")), rs):
        for k, v in rec.items():
            assert r.values[k].entered == v


def test_A11_manhattan_is_new_york_with_the_entered_text_kept():
    r = std(City="Manhattan", Zip="10007")
    assert (r.value("City"), r.values["City"].entered) == ("New York", "Manhattan")


def test_A11_audit_events_hold_no_cell_text():
    for r in rows():
        text = repr(audit_events(r))
        for v in r.values.values():
            if len(v.entered) > 3:
                assert v.entered not in text
