"""Matching calibration in the session (SPEC 8.8, M13 CAL-1 to CAL-8).

Two labelers label a keyed sample of pairs on this computer. Each sees the two records and never the score, band or evidence,
so the number can't lead them. Labels go to calibration\\draft.wcl after each one, and the saved set to calibration\\labeled.wcl,
both "WCL1" plus a DPAPI blob of JSON that holds person keys, evidence codes, scores, bands, labels and labelers' names, never
a name, address, ID or date of a client. Thresholds go to prefs.json with the reviewer and time.
"""
import hashlib
import json
import os
import pathlib
from dataclasses import dataclass, field

from wholecount.engine.calibration.labels import LabelSet, disagreements, settle
from wholecount.engine.calibration.measure import joins_check, known_pairs_check, measure, suggest_line
from wholecount.engine.calibration.note import CalibrationNote
from wholecount.engine.calibration.sample import calibration_pass, draw_sample, settings
from wholecount.engine.outputs.audit_entry import entry

MAGIC = b"WCL1"
DRAFT = "draft.wcl"
LABELED = "labeled.wcl"


class CalibrationRefused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _norm(name):
    return " ".join((name or "").split()).casefold()


def weights_digest(weights):
    return hashlib.sha256(json.dumps(weights, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def current_weights():
    from wholecount.engine.identity import load_settings

    return load_settings()["weights"]


def calibration_dir(session):
    return getattr(session, "calibration_dir", None)


def _pack(data, protect):
    return MAGIC + protect(json.dumps(data, sort_keys=True).encode("utf-8"))


def _unpack(raw, unprotect):
    if not raw.startswith(MAGIC):
        raise CalibrationRefused("not_a_label_file")
    try:
        return json.loads(unprotect(raw[len(MAGIC):]).decode("utf-8"))
    except Exception:  # noqa: BLE001  DPAPI refuses a changed byte; nothing in the file is trusted then
        raise CalibrationRefused("label_file_damaged") from None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".part")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


# Person rows for the batch, from the current results

def person_rows(results):
    from wholecount.engine import pipeline as pl

    r = results
    return [pl.person_row(r.rows[rk], r.system_of_record[rk], r.person_of_record[rk])
            for rk in sorted(r.person_of_record)]


def can_measure(session):
    """Held until a non-practice run has finished and nothing is out of date."""
    r = session.results
    return r is not None and not r.practice and not session.stale


@dataclass(frozen=True)
class KnownPairEntry:
    system_a: str
    client_id_a: str
    system_b: str
    client_id_b: str


@dataclass
class CalibrationSession:
    """One calibration over the current batch. Values the labelers see come from memory and are never written."""
    session: object
    per_band: int
    protect: object = None
    unprotect: object = None
    pairs: tuple = ()
    populations: dict = field(default_factory=dict)
    compared: dict = field(default_factory=dict)
    batch_keys: frozenset = frozenset()
    labelers: list = field(default_factory=list)       # LabelSet, at most two
    settled: dict = field(default_factory=dict)
    known: list = field(default_factory=list)          # (person key a, person key b)
    batch_id: str = ""

    @classmethod
    def draw(cls, session, per_band=None, protect=None, unprotect=None):
        cal = settings()
        per_band = cal["per_band"] if per_band is None else int(per_band)
        if not cal["per_band_min"] <= per_band <= cal["per_band_max"]:
            raise CalibrationRefused("per_band_out_of_range")
        if not can_measure(session):
            raise CalibrationRefused("needs_a_real_run")
        from wholecount.session import dpapi
        from wholecount.session.crosswalk import batch_id_of

        rows = person_rows(session.results)
        res = calibration_pass(rows)
        pairs = draw_sample(res.proposals, res.joins, per_band, session.secret.mac, cal["joins_sample"])
        return cls(session, per_band, protect or dpapi.protect, unprotect or dpapi.unprotect, pairs, dict(res.populations),
                   res.compared, frozenset(r.person_key for r in rows), batch_id=batch_id_of(session, session.results.load))

    # Labeling

    def _labeler(self, reviewer):
        n = _norm(reviewer)
        if not n:
            raise CalibrationRefused("labeler_missing")
        for ls in self.labelers:
            if _norm(ls.labeler) == n:
                return ls
        if len(self.labelers) == 1 and not self.labelers[0].finished:
            raise CalibrationRefused("first_labeler_not_finished")
        if len(self.labelers) >= 2:
            raise CalibrationRefused("labeler_same_person" if any(_norm(x.labeler) == n for x in self.labelers)
                                     else "two_labelers_already")
        ls = LabelSet(reviewer.strip())
        self.labelers.append(ls)
        return ls

    def start(self, reviewer):
        if self.labelers and _norm(self.labelers[0].labeler) == _norm(reviewer) and self.labelers[0].finished:
            raise CalibrationRefused("labeler_same_person")
        return self._labeler(reviewer)

    def label(self, reviewer, pair_id, value):
        if pair_id not in {p.pair_id for p in self.pairs}:
            raise CalibrationRefused("unknown_pair")
        ls = self._labeler(reviewer)
        if ls.finished:
            raise CalibrationRefused("labeler_finished")
        ls.label(pair_id, value)
        self.save_draft()

    def labels_for(self, reviewer, whose=None):
        """A labeler sees only their own labels until both have finished (labels_hidden)."""
        mine = self._labeler(reviewer)
        if whose is None or _norm(whose) == _norm(reviewer):
            return dict(mine.labels)
        if not self.both_finished():
            raise CalibrationRefused("labels_hidden")
        return dict(next(ls for ls in self.labelers if _norm(ls.labeler) == _norm(whose)).labels)

    def finish(self, reviewer):
        self._labeler(reviewer).finished = True
        self.save_draft()

    def both_finished(self):
        return len(self.labelers) == 2 and all(ls.finished for ls in self.labelers)

    def disagreements(self):
        if not self.both_finished():
            raise CalibrationRefused("labels_hidden")
        return [p for p in disagreements(*self.labelers) if p not in self.settled]

    def settle(self, pair_id, value):
        if not self.both_finished():
            raise CalibrationRefused("labels_hidden")
        if value not in ("same", "different", "unsure"):
            raise CalibrationRefused("unknown_label")
        self.settled[pair_id] = value
        self.save_draft()

    def settlement(self):
        return settle(*self.labelers, self.settled)

    # Known pairs

    def add_known(self, entries):
        """Each entry becomes two person keys at once. The Client_ID values are never kept, saved or logged."""
        from wholecount.session import keys

        out = []
        for e in entries:
            a = keys.person_key(self.session.secret, e.system_a, client_id=e.client_id_a)
            b = keys.person_key(self.session.secret, e.system_b, client_id=e.client_id_b)
            out.append(tuple(sorted((a, b))))
        self.known = out
        return known_pairs_check(out, self.compared, self.batch_keys)

    # Results

    def report(self, line=None):
        cal = settings()
        line = line if line is not None else thresholds(self.session)[0]
        st = self.settlement()
        by_id = {p.pair_id: p for p in self.pairs}
        settled = [(by_id[pid].score, by_id[pid].band, lab) for pid, lab in st.labels.items()
                   if by_id[pid].kind == "proposal"]
        m = measure(self.populations, settled)
        joins = [lab for pid, lab in st.labels.items() if by_id[pid].kind == "join"]
        jc = joins_check(len(joins), sum(1 for lab in joins if lab == "different"), cal["joins_target_tenths"])
        kc = known_pairs_check(self.known, self.compared, self.batch_keys)
        return CalibrationReport(m, suggest_line(m, cal["floor"], cal["recall_target_pct"]), line, m.recall(line),
                                 m.missed(line), jc, kc)

    # The draft and the saved labels

    def _dir(self):
        d = calibration_dir(self.session)
        if d is None:
            raise CalibrationRefused("no_folder")
        return pathlib.Path(d)

    def save_draft(self):
        d = calibration_dir(self.session)
        if d is None:
            return
        data = {"batch_id": self.batch_id, "per_band": self.per_band, "settled": self.settled,
                "labelers": [{"name": ls.labeler, "labels": ls.labels, "finished": ls.finished} for ls in self.labelers]}
        _write(pathlib.Path(d) / DRAFT, _pack(data, self.protect))

    def restore_draft(self):
        p = self._dir() / DRAFT
        if not p.exists():
            return False
        data = _unpack(p.read_bytes(), self.unprotect)
        if data.get("batch_id") != self.batch_id:
            raise CalibrationRefused("draft_for_other_batch")
        self.labelers = [LabelSet(x["name"], dict(x["labels"]), bool(x["finished"])) for x in data["labelers"]]
        self.settled = dict(data["settled"])
        return True

    def save(self):
        """Adds this calibration's settled pairs to labeled.wcl (a pair labeled again replaces the older label), removes the
        draft and logs CALIBRATION with both labelers' names and counts."""
        if not self.both_finished():
            raise CalibrationRefused("labels_hidden")
        st = self.settlement()
        by_id = {p.pair_id: p for p in self.pairs}
        old = load_labels(self.session, self.unprotect)
        pairs = {(p["a"], p["b"]): p for p in (old["pairs"] if old else [])}
        names = [ls.labeler for ls in self.labelers]
        for pid, lab in st.labels.items():
            p = by_id[pid]
            pairs[(p.a, p.b)] = {"a": p.a, "b": p.b, "codes": list(p.codes), "score": p.score, "band": p.band,
                                 "kind": p.kind, "label": lab, "labelers": names}
        rep = self.report()
        cal_line = rep.line
        data = {"format": 1, "calibrated_at": self.session.now_iso()[:10], "weights_digest": weights_digest(current_weights()),
                "populations": {str(k): v for k, v in self.populations.items()},
                "joins": [rep.joins.n, rep.joins.wrong, rep.joins.result],
                "known": [{"a": a, "b": b, "compared": True, "score": s} for a, b, s in rep.known.compared] +
                         [{"a": a, "b": b, "compared": False, "score": None} for a, b in self.known
                          if (a, b) not in {(x, y) for x, y, _ in rep.known.compared}],
                "baseline_line": cal_line, "pairs": sorted(pairs.values(), key=lambda x: (x["a"], x["b"]))}
        _write(self._dir() / LABELED, _pack(data, self.protect))
        (self._dir() / DRAFT).unlink(missing_ok=True)
        self.session.log(entry("CALIBRATION", count=[len(st.labels), sum(1 for p in self.pairs if p.kind == "join"),
                                                     len(self.known)],
                               reviewer=names[0], second_reviewer=names[1], time_iso=self.session.now_iso()))
        return len(st.labels)


@dataclass(frozen=True)
class CalibrationReport:
    measures: object
    suggested: int | None
    line: int
    recall: object
    missed: object
    joins: object
    known: object


# Saved labels

@dataclass(frozen=True)
class StoredPair:
    a: str
    b: str
    codes: tuple
    score: int
    band: int | None
    label: str
    kind: str


@dataclass(frozen=True)
class StoredLabels:
    pairs: tuple
    populations: dict
    calibrated_at: str
    weights_digest: str
    baseline_line: int | None
    joins: tuple


def load_labels(session, unprotect=None):
    d = calibration_dir(session)
    if d is None or not (pathlib.Path(d) / LABELED).exists():
        return None
    from wholecount.session import dpapi

    return _unpack((pathlib.Path(d) / LABELED).read_bytes(), unprotect or dpapi.unprotect)


def stored_labels(session, unprotect=None):
    data = load_labels(session, unprotect or getattr(session, "unprotect", None))
    if data is None:
        return None
    pairs = tuple(StoredPair(p["a"], p["b"], tuple(p["codes"]), int(p["score"]), p["band"], p["label"], p.get("kind", "proposal"))
                  for p in data["pairs"])
    return StoredLabels(pairs, {int(k): v for k, v in data["populations"].items()}, data["calibrated_at"],
                        data["weights_digest"], data.get("baseline_line"), tuple(data.get("joins", ())))


def run_regression(session, weights=None, unprotect=None):
    from wholecount.engine.calibration.regression import regression_check

    st = stored_labels(session, unprotect)
    if st is None:
        return None
    proposals = StoredLabels(tuple(p for p in st.pairs if p.kind == "proposal"), st.populations, st.calibrated_at,
                             st.weights_digest, st.baseline_line, st.joins)
    return regression_check(proposals, weights or current_weights(), thresholds(session)[0])


def calibration_note(session, unprotect=None):
    """CAL-8: None until a calibration is saved, and None when the file can't be read (it's then never trusted)."""
    try:
        st = stored_labels(session, unprotect)
    except (CalibrationRefused, OSError):
        return None
    if st is None:
        return None
    line = thresholds(session)[0]
    bands = []
    for b in sorted(st.populations):
        rows = [p for p in st.pairs if p.kind == "proposal" and p.band == b]
        bands.append((b, len(rows), sum(1 for p in rows if p.label == "same")))
    m = measure(st.populations, [(p.score, p.band, p.label) for p in st.pairs if p.kind == "proposal"])
    recall = int(m.recall(line) * 100) if m.estimated_true else None
    return CalibrationNote(st.calibrated_at, tuple(bands), tuple(st.joins), line, recall,
                           st.weights_digest == weights_digest(current_weights()))


# Thresholds (CAL-7)

def thresholds(session):
    """(possible_min, likely_min) in force: the ones saved on this computer, else identity.toml's."""
    from wholecount.engine.identity import load_settings

    t = getattr(session, "thresholds", None)
    if t:
        return int(t[0]), int(t[1])
    b = load_settings()["bands"]
    return int(b["possible_min"]), int(b["likely_min"])


class SetThresholds:
    """Saved to prefs.json with the reviewer and time; applies to this computer, not one batch. Marks identity stale."""

    def __init__(self, possible_min, likely_min):
        lo = settings()["possible_min_lowest"]
        if not (isinstance(possible_min, int) and isinstance(likely_min, int)) or isinstance(possible_min, bool):
            raise CalibrationRefused("thresholds_not_numbers")
        if not lo <= possible_min < likely_min <= 200:
            raise CalibrationRefused("thresholds_out_of_range")
        self.possible_min, self.likely_min = possible_min, likely_min

    def run(self, session, store=None):
        now = session.now_iso()
        who = session.reviewer or ""
        session.thresholds = (self.possible_min, self.likely_min)
        if store is not None:
            store.set_pref("thresholds", {"possible_min": self.possible_min, "likely_min": self.likely_min,
                                          "reviewer": who, "time": now})
        for name, value in (("possible_min", self.possible_min), ("likely_min", self.likely_min)):
            session.log(entry("THRESHOLD_SET", field_name=name, count=value, reviewer=who or None, time_iso=now))


FIELDS = ("name", "dob", "address", "zip", "system")


def side(session, person_key):
    """The first record of one person key, as the labeling screen shows it. From memory only; never written or logged."""
    r = session.results
    rks = sorted(k for k, pk in r.person_of_record.items() if pk == person_key)
    if not rks:
        return {f: "" for f in FIELDS}
    row = r.rows[rks[0]]
    name = " ".join(v for v in (row.value("First_Name"), row.value("Middle_Initial"), row.value("Last_Name")) if v)
    address = " ".join(v for v in (row.value("Address_1"), row.value("Address_2")) if v)
    return {"name": name, "dob": row.value("Date_of_Birth"), "address": address, "zip": row.value("Zip"),
            "system": r.system_of_record.get(rks[0], "")}


def band_edges():
    return settings()["band_edges"]
