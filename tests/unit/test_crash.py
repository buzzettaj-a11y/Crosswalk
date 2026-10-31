"""The crash box (M14 section 3, A-15, H8, H9)."""
import sys

import pytest

from wholecount import copy, crash, errors


def fault(value):
    raise ValueError(f"bad value {value}")


def caught(fn, *a):
    try:
        fn(*a)
    except Exception as e:  # noqa: BLE001
        return e


@pytest.mark.claim("CL-CRASH-01")
def test_the_box_shows_a_stable_code_and_no_message(tmp_path, monkeypatch):
    shown = []
    monkeypatch.chdir(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    a = caught(fault, "Zelphina Quorvath")
    b = caught(fault, "someone else")
    code_a = crash.show(a, lambda text, code: shown.append((text, code)))
    code_b = crash.show(b, lambda text, code: shown.append((text, code)))
    assert code_a == code_b and code_a.startswith("E-")
    text = shown[0][0]
    assert text == copy.get("crash.message", code=code_a)
    assert "Quorvath" not in text and "bad value" not in text
    assert "Nothing was written, and your own files were not changed." in text
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_the_excepthook_runs_the_box_once_and_writes_nothing(tmp_path, monkeypatch):
    shown = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(errors, "_HANDLERS", [])
    old = sys.excepthook
    try:
        crash.install(lambda text, code: shown.append(code))
        exc = caught(fault, "Zelphina Quorvath")
        monkeypatch.setattr(sys, "__stderr__", None)     # a windowed exe has no stderr
        sys.excepthook(type(exc), exc, exc.__traceback__)
    finally:
        sys.excepthook = old
    assert len(shown) == 1 and list(tmp_path.iterdir()) == []


def test_a_different_place_gives_a_different_code():
    def other():
        raise ValueError("x")
    assert crash.show(caught(other), lambda *a: None) != crash.show(caught(fault, "y"), lambda *a: None)
