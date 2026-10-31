"""The guide's example section (CL-GUIDE-EXAMPLE-01): its numbers, both balances included, equal the practice run of the
example files and the counts in EXPECTED.json. Changing one number in a copy is caught."""
import re

import pytest

from tests.conftest import ROOT
from tests.support.example_session import decide, example_session
from wholecount import copy
from wholecount.copy.guide import example_numbers


def numbers_in(text):
    """The numbers in a sentence, leaving out the goal names (Goal 1, Goal 2)."""
    return [int(n.replace(",", "")) for n in re.findall(r"(?<!Goal )\b\d[\d,]*", text)]


def guide_section(text):
    return text.split(copy.get("guide.example.title"), 1)[1]


def check(guide_text, run):
    want = [run[k] for k in ("received", "counted", "not_counted_yet", "aside", "mapped", "not_mapped", "goal1", "goal2")]
    return numbers_in(guide_section(guide_text).split(copy.get("guide.example.p1"), 1)[1]) == want


@pytest.mark.claim("CL-GUIDE-EXAMPLE-01")
def test_the_guide_equals_the_practice_run(tmp_path):
    s = decide(example_session(tmp_path))
    c, loc = s.results.counts, s.results.counts.locations
    run = {"received": s.results.balance.total("received"), "counted": c.counted, "not_counted_yet": c.not_counted_yet,
           "aside": c.set_aside, "mapped": loc.mapped, "not_mapped": loc.not_mapped, "goal1": c.goal1.high,
           "goal2": c.goal2.high}
    assert run == example_numbers()
    text = (ROOT / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
    assert check(text, run)
    assert run["received"] == run["counted"] + run["not_counted_yet"] + run["aside"]
    assert run["counted"] == run["mapped"] + run["not_mapped"]
    bad = text.replace(f"Goal 1 is {run['goal1']:,}", f"Goal 1 is {run['goal1'] + 1:,}")
    assert bad != text and not check(bad, run)
