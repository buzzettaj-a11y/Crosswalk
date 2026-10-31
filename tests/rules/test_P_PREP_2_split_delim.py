"""P-PREP-2: split by a delimiter."""
from tests.support.tables import table
from wholecount.engine.prepare.steps import Step, apply_steps

T = table(["Client_ID", "Name"], [["1", "Lee | Ana | M"], ["2", "Cho | Ben"]])


def test_split_with_names_pads_short_rows():
    p = apply_steps(T, [Step("s", "split_delim", {"column": "Name", "delimiter": "pipe", "names": ["Last", "First"]})])
    assert p.values("Last") == ["Lee", "Cho"] and p.values("First") == ["Ana", "Ben"] and p.values("Name_3") == ["M", ""]


def test_maxsplit_and_custom():
    p = apply_steps(T, [Step("s", "split_delim", {"column": "Name", "custom": " | ", "maxsplit": 1})])
    assert p.values("Name_1") == ["Lee", "Cho"] and p.values("Name_2") == ["Ana | M", "Ben"]


def test_no_delimiter_is_amber():
    r = apply_steps(T, [Step("s", "split_delim", {"column": "Name", "delimiter": "semicolon"})]).results[0]
    assert r.amber and r.amber_reason == "split_found_no_delimiter"


def test_names_are_unique_against_existing_columns():
    p = apply_steps(T, [Step("s", "split_delim", {"column": "Name", "delimiter": "pipe", "names": ["Name", "Client_ID"]})])
    assert [c.name for c in p.columns] == ["Name_2", "Client_ID_2", "Name_3"]
