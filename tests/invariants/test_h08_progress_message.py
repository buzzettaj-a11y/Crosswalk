"""H8: a ProgressMessage can't hold a free string, every message the loader sends is in the registry, and no cell value reaches one."""
import re

import pytest

from tests.support.files import write_text
from tests.support.load import load
from wholecount import copy
from wholecount.engine.progress import ProgressMessage, RecordingSink, SourceRef, Step, StepRef, render


@pytest.mark.parametrize("bad", ["Ana Lee", True, 1.5, None, b"x", ["x"], {"a": 1}])
def test_rejects_anything_but_sourceref_stepref_and_int(bad):
    with pytest.raises(TypeError):
        ProgressMessage("progress.file_count", {"done": bad, "total": 1})


def test_params_must_be_a_dict():
    with pytest.raises(TypeError):
        ProgressMessage("progress.file_count", [("done", 1)])


def test_accepts_the_three_types():
    m = ProgressMessage("progress.reading_source", {"source": SourceRef("A", "a.csv")})
    assert render(m) == "Reading [A] a.csv"
    assert ProgressMessage("x.y", {"s": StepRef(Step.COUNTING), "n": 3}).params["n"] == 3


def test_params_are_copied():
    p = {"done": 1, "total": 2}
    m = ProgressMessage("progress.file_count", p)
    p["done"] = "Ana"
    assert m.params["done"] == 1


def test_every_step_has_copy():
    for s in Step:
        assert copy.get(f"progress.step.{s.value}")
    assert len(Step) == 16


def test_loader_messages_are_registered_and_hold_no_cell_value(tmp_path):
    cells = ["Zelphina", "Quorvath", "QX-778812", "4417 Nowhere Ln"]
    p = write_text(tmp_path, "clients.csv", "Client_ID,First_Name,Last_Name,Address\n" + f"{cells[2]},{cells[0]},{cells[1]},{cells[3]}\n")
    write_text(tmp_path, "bad.csv", "x")
    (tmp_path / "bad.csv").write_bytes(b"A\n\x81\n")
    sink = RecordingSink()
    load([p, tmp_path / "bad.csv"], sink=sink)
    keys = {e.key for e in copy.all_entries()}
    for m in sink.messages():
        assert m.message_id in keys
        text = render(m)
        assert not any(c in text for c in cells), text
        assert not any(c in repr(m) for c in cells)
