"""The calibration pass and the sample (M13 CAL-1)."""
import hashlib
from dataclasses import dataclass

from wholecount.engine.identity import load_settings, resolve
from wholecount.settings.loader import load


def settings():
    return load("calibration")


@dataclass(frozen=True)
class CalPair:
    pair_id: str
    a: str                  # person keys, a < b
    b: str
    score: int
    band: int | None        # 1 to 4, or None for an automatic join
    codes: tuple            # evidence codes
    kind: str = "proposal"  # proposal or join


def pair_id(a, b):
    lo, hi = sorted((a, b))
    return hashlib.sha256((lo + "\x1f" + hi).encode("ascii")).hexdigest()[:12]


def band_of(score, edges=None):
    """1 for 40 to 61, 2 for 62 to 79, 3 for 80 to 99, 4 for 100 or more, None under the floor."""
    edges = edges or settings()["band_edges"]
    if score < edges[0]:
        return None
    for i in range(1, len(edges)):
        if score < edges[i]:
            return i
    return len(edges)


@dataclass(frozen=True)
class PassResult:
    proposals: tuple        # CalPair, scoring at least the floor
    joins: tuple            # CalPair for the four_exact_facts and earlier_batch joins between person keys
    populations: dict       # band -> pairs in the batch
    compared: dict          # (a, b) -> score, every pair the pass scored


def calibration_pass(rows, weights_settings=None):
    """M06 resolve on the batch's person rows with possible_min at the floor, no verdicts, no known masters and
    keep_compared. It touches nothing in the session: no decision, count, stale flag or undo entry."""
    s = load_settings(weights_settings)
    cal = settings()
    s = {**s, "bands": {**s["bands"], "possible_min": cal["floor"]}}
    res = resolve(rows, (), known=None, settings=s, keep_compared=True)
    from wholecount.engine.identity import score_pair, _facts, _records  # noqa: PLC2701

    by_key, _ = _records(rows)
    facts = {k: _facts(rs) for k, rs in by_key.items()}
    proposals, pops = [], {i: 0 for i in range(1, len(cal["band_edges"]) + 1)}
    for p in res.proposals:
        b = band_of(p.score, cal["band_edges"])
        if b is None:
            continue
        pops[b] += 1
        proposals.append(CalPair(pair_id(*p.pair), p.pair[0], p.pair[1], p.score, b, tuple(e.code for e in p.evidence)))
    joins = []
    for j in res.auto_joins:
        if j.reason == "same_system_id":
            continue
        a, b = sorted(j.pair)
        sc = score_pair(facts[a], facts[b], False, s["weights"])
        joins.append(CalPair(pair_id(a, b), a, b, sc.points, None, sc.evidence, "join"))
    compared = {}
    for pair in res.compared or ():
        sc = score_pair(facts[pair[0]], facts[pair[1]], False, s["weights"])
        compared[pair] = sc.points
    return PassResult(tuple(proposals), tuple(joins), pops, compared)


def _order(seed, pairs):
    return sorted(pairs, key=lambda p: hashlib.sha256(seed + p.pair_id.encode("ascii")).digest())


def draw_sample(proposals, joins, per_band, mac, joins_sample=None):
    """Up to per_band pairs from each band and up to joins_sample joins, in a keyed order that doesn't depend on row order."""
    joins_sample = settings()["joins_sample"] if joins_sample is None else joins_sample
    ids = sorted(p.pair_id for p in tuple(proposals) + tuple(joins))
    seed = mac(b"calibration|" + hashlib.sha256("\x1f".join(ids).encode("ascii")).digest())
    out = []
    for b in sorted({p.band for p in proposals}):
        out += _order(seed, [p for p in proposals if p.band == b])[:per_band]
    out += _order(seed, list(joins))[:joins_sample]
    return tuple(out)
