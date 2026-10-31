"""M15 performance finding: the Download stage built every output table twice per draw, only to show row counts. The plan is
reused while the results, the download settings, the log and the reviewer are unchanged, and rebuilt when any of them moves."""
import dataclasses

from tests.support.example_session import decide, example_session
from wholecount.session import commands as C
from wholecount.session import export as ex
from wholecount.session.frame import export_settings
from wholecount.session.pages import export_plan


class Spy:
    def __init__(self, monkeypatch):
        self.n = 0
        real = ex.build_view

        def counted(*a, **k):
            self.n += 1
            return real(*a, **k)
        monkeypatch.setattr(ex, "build_view", counted)


def test_the_same_inputs_reuse_the_plan(tmp_path, monkeypatch):
    s = decide(example_session(tmp_path))
    spy = Spy(monkeypatch)
    a = export_plan(s, export_settings(s))
    b = export_plan(s, export_settings(s))
    assert spy.n == 1 and a == b


def test_any_input_change_builds_it_again(tmp_path, monkeypatch):
    s = example_session(tmp_path)
    spy = Spy(monkeypatch)
    st = export_settings(s)
    first = export_plan(s, st)
    export_plan(s, dataclasses.replace(st, formats={**dict(st.formats), "Final_Clean_Mapped": "json"}) if isinstance(
        st.formats, dict) else dataclasses.replace(st, exact_coordinates=not st.exact_coordinates))
    assert spy.n == 2
    s.history.execute(C.SetReviewer("Someone Else"))        # a log line and a reviewer: both on the plan's log files
    export_plan(s, st)
    assert spy.n == 3
    decide(s)                                               # new results
    after = export_plan(s, st)
    assert spy.n == 4 and after.files != first.files
