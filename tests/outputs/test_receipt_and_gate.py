"""The receipt matches the folder, and the download gate writes nothing while held (OUT-13, SPEC 9.4)."""
import dataclasses
import pathlib

import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.outputs import write
from wholecount.engine.outputs.view import ExportSettings
from wholecount.session import commands as C
from wholecount.session.export import DownloadHeld, download


def test_receipt_matches_folder(tmp_path):
    s = session(tmp_path)
    receipt = write(s, tmp_path / "out", formats={"Unique_Clients": "xlsx", "Final_Clean_Mapped": "json"})
    names = sorted(pathlib.Path(f.path).name for f in receipt.files)
    assert names == sorted(p.name for p in (tmp_path / "out").iterdir())
    clean = next(f for f in receipt.files if f.path.endswith("Final_Clean_Mapped.json"))
    assert (clean.rows, clean.columns) == (13, 20)
    down = s.audit_log[-1][1]
    assert down.code == "DOWNLOAD" and sorted(down.get("file_name")) == names


@pytest.mark.parametrize("why", ["stale", "low_confidence_unacked", "balance_failed"])
def test_held(tmp_path, why):
    s = session(tmp_path, ack=(why != "low_confidence_unacked"))
    if why == "stale":
        s.history.execute(C.SetupChange("export_settings", "x", 1))
    elif why == "balance_failed":
        s.results.balance = dataclasses.replace(s.results.balance, file_rows=s.results.balance.file_rows + 1)
    (tmp_path / "out").mkdir()
    with pytest.raises(DownloadHeld) as e:
        download(s, tmp_path / "out", ExportSettings())
    assert why in e.value.reasons and list((tmp_path / "out").iterdir()) == []


def test_engine_writer_never_imports_the_session():
    import ast
    from tests.conftest import ROOT
    for p in (ROOT / "wholecount" / "engine").rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + \
               [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith("wholecount.session") for m in mods), p
