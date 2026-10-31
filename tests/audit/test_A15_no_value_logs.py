"""A-15: the old app's crash log held client values. Errors name the class, module and line only, and nothing is logged to a
file."""
import logging
import sys

import pytest

from tests.conftest import ROOT
from tests.fixtures.outputs.fixture import VALUES, session
from tests.support.outputs import write
from wholecount import copy
from wholecount.errors import install_excepthook, safe_error_text

SECRET = "Smith Maria 123-45-6789 intake.docx"


@pytest.mark.claim("CL-OUT-14")
def test_safe_error_text_omits_the_message():
    try:
        raise ValueError(SECRET)
    except ValueError as e:
        text = safe_error_text(e)
    assert "Smith" not in text and "123-45-6789" not in text and "ValueError" in text and "Nothing about your clients" in text
    old = sys.excepthook
    try:
        assert install_excepthook() is sys.excepthook
    finally:
        sys.excepthook = old
    assert copy.get("errors.safe_text", kind="X", module="m", line=1)


def test_a_full_session_logs_nothing(tmp_path, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    s = session(tmp_path, "decided")
    write(s, tmp_path / "out")
    out = capsys.readouterr()
    text = out.out + out.err + caplog.text
    for v in VALUES:
        assert v not in text


def test_no_file_handler_in_the_package():
    for p in (ROOT / "wholecount").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert "FileHandler" not in src and "basicConfig(filename" not in src, p
    excepthooks = [p for p in (ROOT / "wholecount").rglob("*.py") if "sys.excepthook =" in p.read_text(encoding="utf-8")]
    assert [p.name for p in excepthooks] == ["errors.py"]
