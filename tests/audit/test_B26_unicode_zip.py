"""B-26 (Medium): full-width and Arabic-Indic digits were accepted as a ZIP. The audit would accept the full-width form;
the spec says five ASCII digits only, and wins."""
from tests.support.std import ids, std


def test_B26_unicode_digits():
    r = std(Zip="１１２０１")
    assert ids(r) == ["zip_unicode_digits"] and r.value("Zip") == "１１２０１"
    assert r.values["Zip"].suggestions == ("11201",)
    r = std(Zip="١١٢٠١")
    assert ids(r) == ["zip_unicode_digits"] and r.values["Zip"].suggestions == ()


def test_B26_numeric_cells():
    assert std(Zip="7030", kinds={"Zip": "number"}).value("Zip") == "07030"
    assert "zip_not_valid" in ids(std(Zip="7030"))
    for v in ("12", "5", "1120134"):
        assert "zip_not_valid" in ids(std(Zip=v, kinds={"Zip": "number"}))
