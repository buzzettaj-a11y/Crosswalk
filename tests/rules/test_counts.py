"""Counting, confidence, commands and staleness (SPEC 7, 3.4, 10.4): COUNT-1 to COUNT-6, CONF-1 to CONF-6, CMD-1 to CMD-5,
STALE-1 to STALE-4."""
import dataclasses

import pytest

from tests.support.session import base, decided, group, rk, snapshot
from wholecount.engine.confidence import location_confidence, master_match_confidence
from wholecount.engine.counts import BalanceError
from wholecount.engine.outputs.audit_entry import SLOTS
from wholecount.session import commands as C
from wholecount.session import staleness
from wholecount.session.staleness import StaleResults


def test_COUNT_1_goals_with_ranges(tmp_path):
    c = base(tmp_path).counts()
    assert (c.goal1.low, c.goal1.high, c.goal2.low, c.goal2.high) == (9, 11, 9, 11)
    assert {p: (r.low, r.high) for p, r in c.per_program.items()} == {"Housing": (3, 4), "Youth": (3, 4), "Workforce": (3, 3)}


def test_COUNT_2_final(tmp_path):
    s = decided(tmp_path)
    assert not s.counts().final
    for p in list(s.results.identity.proposals):
        s.history.execute(C.DecidePair(*p.pair, "different"))
    c = s.counts()
    assert c.final and c.goal1.low == c.goal1.high == 13 and c.not_final_codes == ()


def test_COUNT_3_people_without_program(tmp_path):
    c = base(tmp_path).counts()
    assert (c.people_without_program.low, c.people_without_program.high) == (0, 0)


def test_COUNT_4_dob_coverage(tmp_path):
    assert base(tmp_path).counts().dob_coverage == (13, 13)


def test_COUNT_5_balance_holds(tmp_path):
    s = base(tmp_path)
    b = s.results.balance
    assert b.total("received") == 17 and b.total("counted") == 13
    assert b.total("received") + b.excluded_rows + b.non_table_rows + b.above_header_rows + b.header_rows == b.file_rows


def test_COUNT_6_counts_refuse_when_stale_or_unbalanced(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.SetupChange("steps", ("R.csv", 0), ()))
    with pytest.raises(StaleResults):
        s.counts()
    s.history.undo()
    s.results.balance = dataclasses.replace(s.results.balance, file_rows=s.results.balance.file_rows + 1)
    with pytest.raises(BalanceError):
        s.counts()


def test_CONF_1_to_3_base_and_decided(tmp_path):
    s = base(tmp_path)
    conf = s.results.confidence
    assert conf.level == "low" and [p[0] for p in conf.parts] == ["counted_short", "pairs_open", "placed_short"]
    decide = decided(tmp_path / "d")
    assert decide.results.confidence.level == "medium"
    assert [p for p in decide.results.confidence.parts] == [("counted_short", {"counted": 14, "received": 17}),
                                                            ("pairs_open", {"count": 2}), ("placed_short", {"high": 12, "looked_up": 14})]


def test_CONF_4_acknowledgment_resets(tmp_path):
    s = base(tmp_path)
    assert "low_confidence_unacked" in s.download_gate().reasons
    s.history.execute(C.AcknowledgeLowConfidence())
    assert s.download_gate().held is False
    s.history.execute(C.SetAsideRows([rk(s, "R01")], "test_record"))
    assert "low_confidence_unacked" in s.download_gate().reasons


def test_CONF_5_match_confidence(tmp_path):
    s = base(tmp_path)
    idn = s.results.identity
    ada = s.results.identity.master_of_record[rk(s, "R01")]
    ben = s.results.identity.master_of_record[rk(s, "R02")]
    cara = s.results.identity.master_of_record[rk(s, "R03")]
    assert master_match_confidence(ada, idn) == "certain"
    assert master_match_confidence(ben, idn) == "likely"
    assert master_match_confidence(cara, idn) == "single"


def test_CONF_6_location_confidence(tmp_path):
    s = base(tmp_path)
    assert location_confidence(s.results.outcomes[rk(s, "R01")]) == ("high", None)
    assert location_confidence(s.results.outcomes[rk(s, "R05")]) == ("not_placed", "not_found")


def test_CMD_1_every_command_exists():
    # M08's 17, plus M11's AddSources, UseExampleData, SetKeepSensitive, ConfirmTable, LoadSetup, ConfirmStage and
    # WithdrawProgramDecision
    assert len(C.ALL_COMMANDS) == 24


def test_CMD_2_decisions_recompute_and_setup_waits(tmp_path):
    s = base(tmp_path)
    v = s.results.version
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    assert s.results.version == v + 1 and not s.stale
    s.history.execute(C.SetupChange("steps", ("R.csv", 0), ()))
    assert s.results.version == v + 1 and s.stale


def test_CMD_3_return_to_open(tmp_path):
    s = decided(tmp_path)
    before = snapshot(s)
    s.history.execute(C.ReturnToOpen([rk(s, "R14")]))
    assert s.results.outcomes[rk(s, "R14")].set_aside_reason is None
    s.history.undo()
    assert snapshot(s) == before


def test_CMD_4_entries_use_slots_only(tmp_path):
    s = decided(tmp_path)
    for e in s.audit:
        assert all(name in SLOTS for name, _ in e.fields), e


def test_CMD_5_reviewer_on_decisions_and_entries(tmp_path):
    s = decided(tmp_path)
    assert all(d.reviewer == "Joe" for d in s.decisions)
    assert any(e.get("reviewer") == ["Joe"] for e in s.audit)


def test_STALE_1_nodes_and_sections():
    assert staleness.SECTION_NODE["schema"] == "mappings" and staleness.SECTION_NODE["export_settings"] == "exports"
    assert staleness.downstream("exports") == {"exports"}


def test_STALE_2_declared_covers_actual(tmp_path):
    s = base(tmp_path)
    for cmd in (C.SetupChange("export_settings", "x", 1), C.SetupChange("run_settings", "extra_fields", frozenset({"census_tract"}))):
        s.history.execute(cmd)
        assert cmd.invalidates >= s.stale
        s.history.undo()


def test_STALE_3_undo_restores_without_a_run(tmp_path):
    s = base(tmp_path)
    r = s.results
    s.history.execute(C.SetupChange("sources", str(tmp_path / "S.csv"), False))
    s.history.undo()
    assert s.results is r and not s.stale


def test_STALE_4_download_gate_checks_stale(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.SetupChange("export_settings", "x", 1))
    assert s.download_gate().reasons == ("stale",)


def test_exports_only_stale_for_export_settings(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.SetupChange("export_settings", "x", 1))
    assert s.stale == {"exports"}
    with pytest.raises(StaleResults):
        s.counts()
    assert group(s, "identical")
