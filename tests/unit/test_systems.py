"""SPEC 4.2 and 4.3: source systems and the letter book."""
import pytest

from wholecount.engine.systems import LetterBook, default_systems, group, rename, system_for


def test_one_system_per_file_named_without_extension():
    s = default_systems([("A", "clinic export.csv"), ("B", "C:\\x\\ETO Q3.xlsx")])
    assert [(x.display_name, x.letters) for x in s] == [("clinic export", ("A",)), ("ETO Q3", ("B",))]


def test_grouping_and_rename():
    s = default_systems([("A", "eto_1.csv"), ("B", "other.csv"), ("C", "eto_2.csv")])
    g = group(s, ["A", "C"])
    assert [x.letters for x in g] == [("A", "C"), ("B",)]
    assert system_for(g, "C").display_name == "eto_1"
    r = rename(g, g[0].system_id, " ETO ")
    assert r[0].display_name == "ETO"
    with pytest.raises(ValueError):
        rename(g, g[0].system_id, "  ")


def test_letter_book_reuse_and_no_reuse_after_release():
    book = LetterBook()
    assert [book.assign(fp) for fp in ("f1", "f2", "f1")] == ["A", "B", "A"]
    book.release("A")
    assert book.assign("f3") == "C"
    assert book.assign("f1") == "D"
