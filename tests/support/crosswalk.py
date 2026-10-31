"""Helpers for M13 crosswalk tests: sessions over the crosswalk fixtures that share one crosswalk.db."""
import csv
import io
import pathlib
import random
import shutil

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from tests.support.files_run import ack
from tests.support.outputs import write
from wholecount.session import commands as C
from wholecount.session.crosswalk import TurnOnCrosswalk
from wholecount.session.runner import process

FIX = ROOT / "tests" / "fixtures" / "crosswalk"
TRUTH = [line.split() for line in (FIX / "truth.txt").read_text(encoding="utf-8").splitlines()
         if line.strip() and not line.startswith("#")]


def copy_files(folder, names, shuffle_seed=None, edit=None):
    """Copies fixture files into folder. shuffle_seed reorders each file's body rows; edit(row) may change a row."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for n in names:
        rows = list(csv.reader(io.StringIO((FIX / n).read_text(encoding="utf-8"))))
        head, body = rows[0], rows[1:]
        if shuffle_seed is not None:
            random.Random(f"{shuffle_seed}:{n}").shuffle(body)
        if edit is not None:
            body = [edit(dict(zip(head, r))) for r in body]
            body = [[r[h] for h in head] for r in body]
        with open(folder / n, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([head] + body)
        out.append(folder / n)
    return out


def session(tmp_path, xw_path, names, shuffle_seed=None, edit=None, day=0, **kw):
    """day moves the session's clock on, so a later batch's decisions and masters are later."""
    import datetime as dt

    paths = copy_files(tmp_path / "in", names, shuffle_seed, edit)
    s = r_fixture.session(tmp_path / "w", paths=paths, **kw)
    s.clock.t += dt.timedelta(days=day)
    s.crosswalk_path = xw_path
    return s


def turn_on(s):
    TurnOnCrosswalk("Joe").run(s)


def pk(s, client_id):
    r = s.results
    return next(r.person_of_record[k] for k, row in r.rows.items() if row.value("Client_ID") == client_id
                and k in r.person_of_record)


def master(s, client_id):
    return s.results.identity.master_of[pk(s, client_id)]


def decide(s, a, b, verdict):
    s.history.execute(C.DecidePair(pk(s, a), pk(s, b), verdict))


def decide_truth(s):
    for a, b, v in TRUTH:
        decide(s, a, b, v)


def download(s, folder):
    ack(s)
    return write(s, folder)


def open_pairs(s):
    r = s.results
    cid = {r.person_of_record[k]: r.rows[k].value("Client_ID") for k in r.person_of_record}
    return [tuple(sorted((cid[p.pair[0]], cid[p.pair[1]]))) for p in r.identity.proposals]


def joins(s, reason=None):
    r = s.results
    cid = {r.person_of_record[k]: r.rows[k].value("Client_ID") for k in r.person_of_record}
    return [tuple(sorted((cid.get(j.pair[0], j.pair[0]), cid.get(j.pair[1], j.pair[1]))))
            for j in r.identity.auto_joins if reason is None or j.reason == reason]


def run(s):
    process(s)
    return s


__all__ = ["shutil"]
