"""C-16: the old keep-one-per-program marked rows set aside while they still counted. Every row it sets aside leaves the
counted rows and the clean file."""
from tests.support.session import base, partition
from wholecount.session import commands as C


def test_on_the_base_state(tmp_path):
    s = base(tmp_path)
    before = s.counts()
    clean_before = partition(s.results)[0]
    open_rows = [k for k, o in s.results.outcomes.items() if (o.reasons or any(k in g.members for g in s.results.open_groups))
                 and o.set_aside_reason is None]
    cmd = C.KeepOnePerProgram(open_rows)
    s.history.execute(cmd)
    r = cmd.result
    assert (len(r.kept), len(r.set_aside), len(r.left_alone)) == (2, 2, 4)
    c = s.counts()
    assert (c.counted, c.set_aside) == (before.counted - 2, before.set_aside + 2)
    clean, _, aside = partition(s.results)
    for k, kept in r.set_aside:
        o = s.results.outcomes[k]
        assert o.set_aside_reason == "copy_of" and o.kept_record_key == kept and k not in clean and k in aside
    assert clean_before - clean == {k for k, _ in r.set_aside}
    assert s.audit[-1].get("count") == [2, 2, 4]
