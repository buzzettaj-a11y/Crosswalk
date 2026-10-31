"""Help is complete (M15): every HelpButton id in wholecount/ui has title, purpose and how, no help entry is unused, every
stage has its help, and each how is three sentences or fewer."""
import ast
import re

from tests.conftest import ROOT
from wholecount import copy
from wholecount.copy.registry import _entries
from wholecount.ui.frame.stages import STAGES

UI = ROOT / "wholecount" / "ui"


def placed_ids(root=UI):
    """Every help id a HelpButton or titled() call names. A stage f-string stands for every stage."""
    ids = set()
    for p in root.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("HelpButton", "titled"):
                arg = node.args[-1] if getattr(node.func, "id", "") == "titled" else node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    ids.add(arg.value)
                elif isinstance(arg, ast.JoinedStr):
                    ids |= {f"stage.{s.id}" for s in STAGES}
    return ids


def registry_ids():
    return {m.group(1) for k in _entries() for m in [re.match(r"help\.((?:stage|el)\..+)\.(?:title|purpose|how)$", k)] if m}


def sentences(text):
    return [s for s in re.split(r"(?<=[.?])\s+", text.strip()) if s]


def test_every_placed_id_has_three_parts():
    for hid in placed_ids():
        for part in ("title", "purpose", "how"):
            assert copy.get(f"help.{hid}.{part}"), (hid, part)


def test_no_help_entry_is_unused():
    assert registry_ids() == placed_ids()


def test_every_stage_has_help():
    assert {f"stage.{s.id}" for s in STAGES} <= placed_ids()


def test_each_how_is_three_sentences_or_fewer():
    for hid in registry_ids():
        assert len(sentences(copy.get(f"help.{hid}.how"))) <= 3, hid


def test_the_elements_the_milestone_names_are_placed():
    want = {"el.confidence", "el.pairs", "el.program_groups", "el.map_points", "el.record_keys", "el.balances",
            "el.not_mapped", "el.set_aside", "el.reviewer", "el.ledger"}
    assert want <= placed_ids()


def test_negative_control(tmp_path):
    (tmp_path / "x.py").write_text('HelpButton("el.nope")\n')
    assert placed_ids(tmp_path) == {"el.nope"} and "el.nope" not in registry_ids()
