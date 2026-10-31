"""P-PREP-1 and P-STD-1 casing: clean columns. A clean step adds <col>_clean and never changes the source."""
import pytest

from tests.support.tables import table
from wholecount.engine.prepare.casing import title_address, title_name
from wholecount.engine.prepare.steps import Step, apply_steps, clean_value


@pytest.mark.parametrize("raw,out", [
    ("MCMAHON", "McMahon"), ("MCE", "Mce"), ("MACARTHUR", "MacArthur"), ("MACHADO", "Machado"), ("O’BRIEN", "O’Brien"),
    ("D'ANGELO", "D'Angelo"), ("SMITH-JONES", "Smith-Jones"), ("DE LA CRUZ", "De la Cruz"), ("DINAPOLI", "DiNapoli"),
    ("DEJESUS", "DeJesus"), ("LEBRON", "LeBron"), ("DiNapoli", "DiNapoli"), ("LaGuardia", "LaGuardia"), ("mELINDA", "mELINDA"),
    ("o'brien", "O'Brien"), ("john iii", "John III"),
])
def test_title_name_worked_cases(raw, out):
    assert title_name(raw) == out


def test_title_address():
    assert title_address("117-19 45TH AVE NW") == "117-19 45th Ave NW"
    assert title_address("123 Main St") == "123 Main St"


@pytest.mark.parametrize("case,raw,out", [
    ("none", "  ana   LEE ", "ana LEE"), ("upper", "ana lee", "ANA LEE"), ("lower", "ANA LEE", "ana lee"),
    ("title_name", "ANA LEE", "Ana Lee"), ("title_address", "12 MAIN ST", "12 Main St"),
])
def test_case_modes(case, raw, out):
    assert clean_value(raw, case) == out


def test_junk_and_edge_punctuation():
    assert clean_value("Ana^ Lee**", strip_junk=True) == "Ana Lee"
    assert clean_value("“Ana”", strip_junk=True) == '"Ana"'
    assert clean_value("St..", strip_junk=True) == "St."
    assert clean_value(", Ana Lee -", strip_edge_punctuation=True) == "Ana Lee"


def test_unknown_case_raises():
    with pytest.raises(ValueError):
        clean_value("x", "sentence")


def test_step_adds_a_column_and_keeps_the_source():
    t = table(["Client_ID", "Last Name"], [["1", "MCMAHON"], ["2", "Lee"]])
    before = [list(r) for r in t.rows]
    p = apply_steps(t, [Step("s1", "clean", {"columns": ["Last Name"], "case": "title_name"})])
    assert p.values("Last Name_clean") == ["McMahon", "Lee"]
    assert t.rows == before
    assert not p.results[0].amber


def test_a_clean_that_changes_nothing_is_amber():
    t = table(["Client_ID", "Last Name"], [["1", "Lee"], ["2", "Cho"]])
    r = apply_steps(t, [Step("s1", "clean", {"columns": ["Last Name"]})]).results[0]
    assert r.amber and r.amber_reason == "clean_changed_nothing"
