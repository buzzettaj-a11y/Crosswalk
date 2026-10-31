"""The ledger (SPEC 7.1 to 7.4, 11.3): before-run sentences, ranges and final, the two equations, stale and unbalanced."""
import re

import pytest
from PySide6.QtWidgets import QLabel

from tools import screen_fixtures as F
from wholecount import copy
from wholecount.ui.frame.ledger import LedgerPanel
from wholecount.ui.frame.view import RESULT_STAGES


def texts(widget):
    return [w.text() for w in widget.findChildren(QLabel) if w.isVisibleTo(widget)]


def panel(qtbot, view):
    p = LedgerPanel()
    qtbot.addWidget(p)
    p.update_view(view)
    return p


def named(p, name):
    return p.findChild(QLabel, name)


def test_before_run_sentences(qtbot):
    p = panel(qtbot, F.idle())
    t = texts(p)
    for key in ("ledger.batch.empty", "ledger.standing.before", "ledger.counts.before", "ledger.conf.before",
                "ledger.loc.before"):
        assert copy.get(key) in t


def test_running_never_shows_half_a_count(qtbot):
    p = panel(qtbot, F.after_run(running=True))
    t = " ".join(texts(p.counts) + texts(p.standing))
    assert copy.get("ledger.standing.running") in t
    assert "5,940" not in t and "6,084" not in t


@pytest.mark.claim("CL-RANGE-01")
@pytest.mark.claim("CL-RANGE-04")
def test_range_until_pairs(qtbot):
    p = panel(qtbot, F.after_run())
    assert named(p, "goal1Count").text() == "5,940"
    assert named(p, "goal1Sub").text() == "unique clients, a range to 5,954 until 14 pairs are decided"
    assert named(p, "goal2Sub").text() == "unique clients by program, a range to 7,121 until 14 pairs are decided"
    assert "final" not in " ".join(texts(p.counts))


@pytest.mark.claim("CL-RANGE-02")
@pytest.mark.claim("CL-RANGE-05")
def test_range_until_pairs_and_groups(qtbot):
    p = panel(qtbot, F.after_run(counts=F.counts(open_groups=3)))
    assert named(p, "goal1Sub").text().endswith("until 14 pairs and 3 copy groups are decided")
    assert named(p, "goal2Sub").text().endswith("until 14 pairs and 3 copy groups are decided")


@pytest.mark.claim("CL-RANGE-03")
@pytest.mark.claim("CL-RANGE-06")
def test_range_until_groups_only(qtbot):
    p = panel(qtbot, F.after_run(counts=F.counts(open_pairs=0, open_groups=2)))
    assert named(p, "goal1Sub").text().endswith("until 2 copy groups are decided")
    assert named(p, "goal2Sub").text().startswith("unique clients by program")


@pytest.mark.claim("CL-FINAL-01")
@pytest.mark.claim("CL-FINAL-03")
def test_final_only_when_the_engine_says_so(qtbot):
    p = panel(qtbot, F.after_run(counts=F.counts(final=True, open_pairs=0, not_counted_yet=0)))
    assert named(p, "goal1Sub").text() == "unique clients, final"
    assert named(p, "goal2Sub").text() == "unique clients by program, final"
    assert named(p, "settled") is None


@pytest.mark.claim("CL-FINAL-02")
def test_pairs_closed_but_rows_open_is_settled_not_final(qtbot):
    p = panel(qtbot, F.after_run(counts=F.counts(open_pairs=0)))
    t = " ".join(texts(p.counts))
    assert "final" not in t
    assert named(p, "settled").text() == "Settled for the rows counted so far. 1,232 rows aren't counted yet."


@pytest.mark.claim("CL-FINAL-01")
def test_final_follows_the_engine_flag_not_the_ui(tmp_path):
    """COUNT-2: final only with no pairs, no copy groups and no rows not counted yet, and the engine sets it."""
    from tests.support.session import decide_all, decided
    from wholecount.ui.frame.view import build_view

    s = decided(tmp_path)
    v = build_view(s)
    assert v.is_final == s.results.counts.final
    assert not v.is_final and v.counts.open_pairs
    decide_all(s)
    v = build_view(s)
    c = s.results.counts
    assert v.is_final == (c.open_pairs == 0 and c.open_copy_groups == 0 and c.not_counted_yet == 0) == c.final


@pytest.mark.claim("CL-BALANCE-01")
@pytest.mark.claim("CL-BALANCE-LOC-01")
def test_equations_come_from_the_view(qtbot):
    v = F.after_run()
    p = panel(qtbot, v)
    (k1, p1), (k2, p2) = v.counts.lines
    assert named(p, "standingSum").text() == copy.get(k1, **p1) == \
        "6,084 + 1,232 + 96 = 7,412. The three add up to the rows received."
    assert named(p, "locSum").text() == copy.get(k2, **p2) == \
        "5,802 + 198 + 84 = 6,084. The three add up to the rows counted."


@pytest.mark.claim("CL-BALANCE-01")
@pytest.mark.claim("CL-BALANCE-LOC-01")
def test_engine_equations_add_up_after_every_command(tmp_path):
    from tests.support.session import base, group, rk
    from wholecount.session import commands as C
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    for cmd in (None, C.SetAsideRows([rk(s, "R14")], "out_of_scope"),
                C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0])):
        if cmd:
            s.history.execute(cmd)
        (_, rows), (_, loc) = build_view(s).counts.lines
        assert rows["counted"] + rows["not_counted_yet"] + rows["set_aside"] == rows["received"]
        assert loc["high"] + loc["low"] + loc["not_mapped"] == loc["counted"] == rows["counted"]


def test_no_widget_builds_an_equation():
    from tests.conftest import ROOT

    for p in (ROOT / "wholecount" / "ui").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert not re.search(r"""f["'][^"']*\{[^}]*\}\s*\+\s*\{""", src), p
        assert " = {received}" not in src and "= {counted}" not in src, p


@pytest.mark.claim("CL-BALANCE-HELD-01")
def test_unbalanced_shows_the_error_and_no_counts(qtbot):
    p = panel(qtbot, F.after_run(counts=F.counts(balance_ok=False)))
    assert named(p, "unbalanced").text() == copy.get("ledger.standing.unbalanced")
    assert "6,084" in " ".join(texts(p.standing))
    t = " ".join(texts(p.counts))
    assert "5,940" not in t and "7,106" not in t


@pytest.mark.claim("CL-BALANCE-HELD-01")
def test_session_refuses_counts_when_unbalanced(tmp_path):
    from dataclasses import replace

    from tests.support.session import base
    from wholecount.engine.counts import BalanceError
    from wholecount.ui.frame.view import counts_view

    s = base(tmp_path)
    t = s.results.balance.tables[0]
    s.results.balance = replace(s.results.balance, tables=(replace(t, counted=t.counted + 1),) + s.results.balance.tables[1:])
    with pytest.raises(BalanceError):
        s.counts()
    assert s.download_gate().held
    assert counts_view(s.results).balance_ok is False


@pytest.mark.claim("CL-STALE-COUNTS-01")
def test_stale_view_never_shows_a_number_in_counts(qtbot):
    p = panel(qtbot, F.after_run(stale=frozenset(RESULT_STAGES), counts=None))
    t = " ".join(texts(p.counts))
    assert copy.get("ledger.counts.stale") in t
    assert not re.search(r"\d", t.replace(copy.get("ledger.counts.stale"), ""))


@pytest.mark.claim("CL-STALE-COUNTS-01")
def test_session_view_drops_counts_when_stale(tmp_path):
    from tests.support.session import base
    from wholecount.session.commands import SetupChange
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    assert build_view(s).counts is not None
    s.history.execute(SetupChange("run_settings", "extra_fields", ()))
    v = build_view(s)
    assert v.results_stale and v.counts is None and v.confidence is None


def test_location_breakdown_rows_show_only_above_zero(qtbot):
    p = panel(qtbot, F.after_run())
    for reason, n in (("no_fixed_address", 31), ("outside_nyc", 22), ("address_problem", 19), ("not_found", 12)):
        assert named(p, f"loc_{reason}") is not None
    assert named(p, "loc_no_geocoder") is None


def test_location_problems_never_change_the_count(qtbot):
    v = F.after_run()
    assert v.counts.locations.not_mapped == 84
    p = panel(qtbot, v)
    assert "6,084" in " ".join(texts(p.standing))


@pytest.mark.claim("CL-LOC-VERIFIED-01")
def test_weak_match_is_never_labeled_verified(tmp_path):
    """A low-confidence placement reads Mapped, low confidence in every output, never Verified."""
    from tests.support.session import base
    from wholecount.engine.outputs import tables

    s = base(tmp_path)
    from wholecount.session.export import build_view as out_view
    view = out_view(s)
    for r in view.rows:
        if r.location and r.location[0] == "mapped" and r.location[1] == "low":
            assert tables.location_status_text(r) != copy.get("location.verified")
    assert copy.get("location.verified") not in {tables.location_status_text(r) for r in view.rows}


def test_three_stage_sections_render(qtbot):
    from wholecount.ui.frame.sections import SECTIONS

    v = F.after_run(steps_noop=1, steps_added=2, map_wrong=1, program_groups_open=2,
                    preview=F.after_run().preview.__class__(5931, 7090, "14:12", stale=True))
    for sid, cls in SECTIONS.items():
        w = cls(v)
        qtbot.addWidget(w)
        assert texts(w)
    prog = " ".join(texts(SECTIONS["programs"](v)))
    assert "from the preview" in prog and "Preview taken at 14:12" in prog
    assert copy.get("ledger.section.prepare.note") in texts(SECTIONS["prepare"](v))


@pytest.mark.claim("CL-STEPS-ADD-01")
def test_steps_add_columns_and_remove_nothing():
    """Behavior behind the note: every kind of tidy-up step adds new columns and leaves the source cells as they were."""
    from tests.support.tables import table
    from wholecount.engine.prepare.steps import Step, apply_steps, source_cells_changed

    t = table(["Client_ID", "Name", "Address", "Zip"],
              [["1", "LEE, ANA", "12 MAIN ST APT 4 BROOKLYN NY 11201", "11201"], ["2", "ROE; BO", "5 ELM AVE", ""]])
    before = [list(r) for r in t.rows]
    steps = [Step("s1", "clean", {"columns": ["Name"], "case": "title_name"}),
             Step("s2", "split_delim", {"column": "Name", "delimiter": "comma"}),
             Step("s3", "split_address", {"column": "Address"}),
             Step("s4", "split_name", {"column": "Name"}),
             Step("s5", "calc_zip", {"street_col": "Address", "zip_col": "Zip"})]
    p = apply_steps(t, steps)
    assert source_cells_changed(before, t) == 0
    assert p.names()[:4] == ["Client_ID", "Name", "Address", "Zip"]
    assert len(p.names()) > 4 and all(c.name not in t.headers for c in p.columns)


@pytest.mark.claim("CL-PRACTICE-02")
def test_practice_line_only_for_practice(qtbot):
    assert named(panel(qtbot, F.after_run(practice=True)), "practiceLine").text() == copy.get("ledger.batch.practice")
    assert named(panel(qtbot, F.after_run()), "practiceLine") is None
