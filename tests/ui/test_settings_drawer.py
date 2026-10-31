"""The Settings drawer (spec review notes for SPEC 11.3): the link opens it, three sections draw, the switch updates the
footer trust sentence, and prefs.json holds no client value."""
import json

import pytest

from tests.ui.conftest import Confirm, settle
from tools import screen_fixtures as F
from wholecount import copy


def test_link_opens_three_sections(make_window, qapp):
    w = make_window(F.after_run())
    w.ledger.settings.click()
    settle(qapp)
    s = w.settings
    assert s.isVisible()
    assert s.reviewer.text() == "Reviewer: J. Rivera"
    assert s.table.rows and s.switch.check.isChecked()


@pytest.mark.claim("CL-TRUST-SAVED-01")
def test_toggling_saved_progress_updates_the_footer(make_window, qapp):
    w = make_window(F.after_run(), confirm=Confirm(True))
    assert copy.get("ledger.foot.trust_saved") in w.ledger.trust.text()
    w.settings.open_()
    w.settings.switch.check.setChecked(False)
    settle(qapp)
    assert copy.get("ledger.foot.trust_saved") not in w.ledger.trust.text()
    assert w.your_data.switch.check.isChecked() is False


def test_prefs_json_holds_settings_only(tmp_path):
    from tests.support.fake_dpapi import FakeDpapi
    from tests.support.session import base
    from wholecount.session.store import Store
    from wholecount.ui.frame.bridge import SessionBridge

    s = base(tmp_path / "w")
    fd = FakeDpapi()
    s.store = Store(tmp_path / "store", fd.protect, fd.unprotect)
    b = SessionBridge(s, {"saved_progress": True})
    b.set_saved_progress(False)
    b.set_saved_progress(True)
    raw = (tmp_path / "store" / "prefs.json").read_text(encoding="utf-8")
    assert set(json.loads(raw)) == {"saved_progress"}
    for r in s.results.rows.values():
        for _, v in r.values.items():
            if v.entered and len(v.entered) >= 3:
                assert v.entered not in raw
