"""SPEC 5.1: keys don't depend on add order, survive a re-export, and depend on the secret."""
import csv
import io
import pathlib

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.conftest import ROOT
from tests.support.load import load
from tests.support.secrets import OTHER_SECRET
from wholecount.engine.read.tables import rebuild_with_header

DATA = ROOT / "wholecount" / "sample_data"
NAMES = ["example_clinic.csv", "example_housing.xlsx", "example_partner.tsv", "example_portal.json", "example_state.xml"]
BASE = load([DATA / n for n in NAMES])


def keyed(result):
    return {t.key: t.record_keys for t in result.tables}


@settings(max_examples=12, deadline=None)
@given(st.permutations(NAMES))
def test_add_order_changes_only_letters(order):
    r = load([DATA / n for n in order])
    assert keyed(r) == keyed(BASE)
    assert [f.letter for f in r.files] == ["A", "B", "C", "D", "E"]


def test_re_export_keeps_every_other_record_key(tmp_path):
    rows = list(csv.reader(io.StringIO((DATA / "example_clinic.csv").read_text(encoding="utf-8"), newline="")))
    before = load([DATA / "example_clinic.csv"]).tables[0]
    changed = [list(r) for r in rows]
    changed[5][4] = "Changed Program"
    changed.insert(1, ["C-9999", "Newcomer, Ada", "1 Centre St New York NY 10007", "01/02/1990", "Housing Assistance"])
    p = tmp_path / "example_clinic.csv"
    buf = io.StringIO(newline="")
    csv.writer(buf).writerows(changed)
    p.write_text(buf.getvalue(), encoding="utf-8")
    after = load([p]).tables[0]
    assert after.key == before.key
    old = dict(zip(before.record_keys, map(tuple, before.rows)))
    new = set(after.record_keys)
    kept = [k for k, row in old.items() if row != tuple(rows[5])]
    assert all(k in new for k in kept)
    changed_key = before.record_keys[before.rows.index(rows[5])]
    assert changed_key not in new
    assert len(new - set(old)) == 2


def test_two_secrets_give_disjoint_keys():
    other = load([DATA / n for n in NAMES], secret=OTHER_SECRET)
    a = {k for ks in keyed(BASE).values() for k in ks}
    b = {k for ks in keyed(other).values() for k in ks}
    assert a and b and not (a & b)


def test_ticking_a_continuation_changes_no_key():
    rows = [["Client_ID", "First_Name", "Last_Name"], ["1", "a", "b"], [""], ["2", "c", "d"]]
    from tests.support.grids import grid
    from wholecount.engine.read.tables import find_tables
    from wholecount.session.loader import key_tables
    from wholecount.session.secret_store import InstallSecret
    from tests.support.secrets import TEST_SECRET
    t = find_tables(grid(rows)).tables
    k1 = key_tables(InstallSecret(TEST_SECRET), "f_csv", t)[0].record_keys
    t[0].blocks[1].included = False
    assert key_tables(InstallSecret(TEST_SECRET), "f_csv", t)[0].record_keys == k1


def test_two_files_with_one_name_are_the_stated_exception(tmp_path):
    """The second file with a normalized name takes ~ and its fingerprint, so which one is second depends on add order."""
    a = tmp_path / "x" / "clients.csv"
    b = tmp_path / "y" / "Clients.csv"
    for p, v in ((a, "1"), (b, "2")):
        p.parent.mkdir()
        p.write_text(f"Client_ID,First_Name,Last_Name\n{v},Ana,Lee\n", encoding="utf-8")
    ab = [t.key for t in load([a, b]).tables]
    ba = [t.key for t in load([b, a]).tables]
    assert ab[0].startswith("clients_csv :: ") and "~" in ab[1]
    assert set(ab) != set(ba)
