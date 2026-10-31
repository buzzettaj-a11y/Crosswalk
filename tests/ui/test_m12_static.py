"""Static scans of stages 06 to 09: the only free-text boxes are the allowed ones, and no setting offers what SPEC drops."""
import ast

import pytest

from tests.conftest import ROOT

STAGES = ROOT / "wholecount" / "ui" / "stages"
# (file, attribute or variable the box is bound to). Two are searches that filter the view and write nothing. The other
# three are the reviewer's name, the second reviewer's name and the 120-character Other note, none of them a client value.
ALLOWED = {("review/dialogs.py", "name"), ("review/dialogs.py", "second"), ("review/dialogs.py", "note"),
           ("review/queue.py", "search"), ("summary/body.py", "search")}
FREE_TEXT = {"QLineEdit", "QTextEdit", "QPlainTextEdit"}


def boxes():
    out = set()
    for sub in ("run", "review", "summary", "export"):
        for p in (STAGES / sub).glob("*.py"):
            tree = ast.parse(p.read_text(encoding="utf-8"))
            bound = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", "") in FREE_TEXT:
                    t = n.targets[0]
                    bound.add(id(n.value))
                    out.add((p.relative_to(STAGES).as_posix(), t.attr if isinstance(t, ast.Attribute) else t.id))
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") in FREE_TEXT and id(n) not in bound:
                    out.add((p.relative_to(STAGES).as_posix(), "?"))
    return out


def test_only_the_allowed_free_text_boxes_exist():
    assert boxes() == ALLOWED


def test_the_other_note_is_capped_and_only_for_other():
    from wholecount.session import commands as C
    from wholecount.session.commands import Refused

    with pytest.raises(Refused):
        C.SetAsideRows(["k"], "test_record", "a note")
    with pytest.raises(Refused):
        C.SetAsideRows(["k"], "other", "x" * 121)


def test_process_offers_no_offset_seed_or_unplaced_setting():
    """The only run setting is the extra Geosupport fields (P-GEO-7, P-VAL-2)."""
    import re

    text = (STAGES / "run" / "body.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'SetupChange\("run_settings", "([a-z_]+)"', text))
    assert keys == {"extra_fields"}
    lowered = text.lower()
    for word in ("offset", "seed", "unplaced"):
        assert word not in lowered, word
