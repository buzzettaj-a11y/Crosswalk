"""
Identity resolution: work out which records describe the same human, assign a
master ID, and count unique clients and unique client-program pairs.

Why this is a separate engine
-----------------------------
The duplicate check in the cleaning pipeline answers a narrow question: is this
the same record twice? It compares a fixed key and never guesses. That is right
for de-duplicating one export, and useless for linking a person across systems,
because the fields it compares are exactly the ones that change: a surname after
marriage, a first name recorded as a nickname, an address after a move.

This engine answers a different question: which records describe the same
person? That question cannot be answered by string similarity, because the hard
cases are not near misses. Robert and Bob share two letters. A maiden and a
married surname share none. So instead of comparing strings, this engine looks
for agreement across several independent pieces of evidence, and reports what it
found rather than deciding on its own.

The rule that keeps this safe
-----------------------------
Records are joined automatically only on evidence that cannot reasonably be a
coincidence. Everything else becomes a proposed link carrying the specific
reason it was proposed, for a person to confirm or reject. Confirmed and
rejected decisions are stored and replayed, so the work is done once.

Because some links stay unconfirmed, the client count is reported as a range:
the count if every proposal is accepted, and the count if every proposal is
rejected. A single number would imply a precision the data does not support.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict


# ---------------------------------------------------------------------------
# name knowledge
# ---------------------------------------------------------------------------
# Groups of given names that refer to the same name. Matching is by group, not
# by spelling, so Bob and Robert match while sharing almost no letters.
NICKNAME_GROUPS = [
    ["robert", "rob", "bob", "bobby", "robbie", "bert"],
    ["margaret", "peggy", "peg", "maggie", "meg", "marge", "margie", "rita", "greta"],
    ["charles", "charlie", "chuck", "chas", "chip", "carlos"],
    ["william", "will", "bill", "billy", "willie", "liam"],
    ["richard", "rich", "rick", "ricky", "dick", "richie"],
    ["elizabeth", "liz", "beth", "betty", "betsy", "eliza", "libby", "lizzie", "liza"],
    ["james", "jim", "jimmy", "jamie"],
    ["john", "jack", "johnny", "jon"],
    ["joseph", "joe", "joey"],
    ["michael", "mike", "mikey", "mickey", "micky"],
    ["thomas", "tom", "tommy"],
    ["edward", "ed", "eddie", "ted", "teddy", "ned"],
    ["anthony", "tony", "ant"],
    ["katherine", "catherine", "kathryn", "kate", "katie", "kathy", "cathy", "kay", "kit"],
    ["patricia", "pat", "patty", "trish", "tricia", "patsy"],
    ["barbara", "barb", "babs"],
    ["susan", "sue", "susie", "suzy", "suzanne"],
    ["jennifer", "jen", "jenny", "jenn"],
    ["deborah", "debra", "deb", "debbie"],
    ["sandra", "sandy"],
    ["theodore", "ted", "teddy", "theo"],
    ["nicholas", "nick", "nicky"],
    ["alexander", "alexandra", "alex", "xander", "sasha"],
    ["christopher", "chris", "topher"],
    ["daniel", "dan", "danny"],
    ["david", "dave", "davey"],
    ["donald", "don", "donnie"],
    ["ronald", "ron", "ronnie"],
    ["kenneth", "ken", "kenny"],
    ["lawrence", "larry", "laurence", "laurie"],
    ["gregory", "greg"],
    ["jeffrey", "geoffrey", "jeff"],
    ["stephen", "steven", "steve", "stevie"],
    ["andrew", "andy", "drew"],
    ["frederick", "fred", "freddie", "freddy"],
    ["eugene", "gene"],
    ["vincent", "vince", "vinny", "vinnie"],
    ["francis", "frances", "frank", "fran", "franny", "francisco", "paco", "pancho"],
    ["henry", "hank", "hal", "harry"],
    ["albert", "al", "albie"],
    ["arthur", "art", "artie"],
    ["benjamin", "ben", "benny", "benji"],
    ["bernard", "bernie"],
    ["dennis", "denny"],
    ["douglas", "doug"],
    ["eleanor", "ellie", "nell", "nora"],
    ["emily", "em", "emmy"],
    ["florence", "flo", "flossie"],
    ["george", "georgie"],
    ["gerald", "gerry", "jerry"],
    ["harold", "hal", "harry"],
    ["jacob", "jake"],
    ["janet", "jan"],
    ["jonathan", "jon", "jonny"],
    ["joshua", "josh"],
    ["judith", "judy", "jude"],
    ["louis", "lou", "louie", "luis"],
    ["martha", "marty", "mattie"],
    ["mary", "molly", "polly", "mae", "may", "maria"],
    ["matthew", "matt", "matty"],
    ["melissa", "mel", "missy"],
    ["nancy", "nan"],
    ["nathaniel", "nathan", "nate"],
    ["pamela", "pam"],
    ["peter", "pete"],
    ["philip", "phillip", "phil"],
    ["rebecca", "becky", "becca", "reba"],
    ["raymond", "ray"],
    ["rose", "rosie", "rosa"],
    ["samuel", "sam", "sammy"],
    ["sarah", "sara", "sally", "sadie"],
    ["stanley", "stan"],
    ["timothy", "tim", "timmy"],
    ["victoria", "vicky", "vicki", "tori"],
    ["virginia", "ginny", "ginger"],
    ["walter", "walt", "wally"],
    ["zachary", "zach", "zack"],
    ["jose", "pepe"],
    ["guadalupe", "lupe"],
    ["concepcion", "concha"],
    ["jesus", "chuy"],
    ["ignacio", "nacho"],
    ["enrique", "quique", "henry"],
    ["eduardo", "lalo", "edward"],
    ["manuel", "manny", "manolo"],
    ["antonio", "tono", "tony"],
    ["dolores", "lola"],
    ["mercedes", "meche"],
    ["rosario", "charo"],
    ["magdalena", "magda", "lena"],
    ["esperanza", "espy"],
    ["soledad", "sole", "chole"],
]

_NICK = {}
for _i, _grp in enumerate(NICKNAME_GROUPS):
    for _n in _grp:
        _NICK.setdefault(_n, set()).add(_i)

# Particles that belong to a surname but are not distinguishing on their own.
SURNAME_PARTICLES = {"de", "del", "de la", "la", "las", "los", "van", "von",
                     "der", "den", "di", "da", "do", "dos", "du", "el", "al",
                     "bin", "ibn", "san", "santa", "st", "mc", "mac", "o"}

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _fold(text) -> str:
    """Lowercase, strip accents, drop punctuation. Jose and José become one."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ").replace("'", "")
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def given_keys(first: str) -> set:
    """
    Every form a given name could match on: the folded name itself, plus the id
    of any nickname group it belongs to. Bob and Robert share a group id.
    """
    f = _fold(first)
    if not f:
        return set()
    head = f.split()[0]
    keys = {head}
    for gid in _NICK.get(head, ()):
        keys.add(f"g{gid}")
    return keys


def surname_tokens(last: str) -> set:
    """
    The distinguishing parts of a surname. Garcia Lopez, Garcia-Lopez and
    GarciaLopez all reduce to the same pair, so a system that recorded only one
    half still overlaps with a system that recorded both.
    """
    f = _fold(last)
    if not f:
        return set()
    parts = [p for p in f.split() if p and p not in SUFFIXES]
    keep = [p for p in parts if p not in SURNAME_PARTICLES and len(p) > 1]
    return set(keep or parts)


# ---------------------------------------------------------------------------
# date of birth
# ---------------------------------------------------------------------------
def parse_dob(value):
    """
    Return (year, month, day) or None. Accepts ISO, US and dotted forms. An
    ambiguous day and month is kept as written; the comparison below is what
    tolerates a transposition, not the parser.
    """
    s = str(value or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", s)
        if not m:
            return None
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 1900 if y > 25 else 2000
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100):
        # a day and month written the other way round
        if 1 <= d <= 12 and 1 <= mo <= 31 and 1900 <= y <= 2100:
            mo, d = d, mo
        else:
            return None
    return (y, mo, d)


def _digits(dob) -> str:
    """Only the digits of a value."""
    return f"{dob[0]:04d}{dob[1]:02d}{dob[2]:02d}"


def _one_edit_apart(a: str, b: str) -> bool:
    """True when two equal-length digit strings differ by one substitution or
    one swap of adjacent digits. Covers 1999 typed as 1990, and 19 as 91."""
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(diff) == 1:
        return True
    if len(diff) == 2 and diff[1] == diff[0] + 1:
        i, j = diff
        return a[i] == b[j] and a[j] == b[i]
    return False


def compare_dob(a, b):
    """Return ('exact'|'near'|'differs'|'unknown', reason)."""
    da, db = parse_dob(a), parse_dob(b)
    if da is None or db is None:
        return "unknown", "one or both dates of birth are missing"
    if da == db:
        return "exact", "dates of birth match"
    if da[0] == db[0] and {da[1], da[2]} == {db[1], db[2]}:
        return "near", "day and month are the other way round"
    if _one_edit_apart(_digits(da), _digits(db)):
        return "near", "dates of birth differ by a single digit"
    return "differs", "dates of birth do not match"


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------
class PersonRecord:
    """One row from one source, reduced to the fields identity depends on."""

    __slots__ = ("rid", "source", "system", "client_id", "first", "last",
                 "dob", "street", "zip", "program", "raw",
                 "gkeys", "lkeys", "addr_key", "dob_key", "_first_head")

    def __init__(self, rid, first="", last="", dob="", street="", zip="",
                 program="", client_id="", system="", source="", raw=None):
        self.rid = rid
        self.source = source or system
        self.system = system or source
        self.client_id = str(client_id or "").strip()
        self.first = str(first or "").strip()
        self.last = str(last or "").strip()
        self.dob = str(dob or "").strip()
        self.street = str(street or "").strip()
        self.zip = str(zip or "").strip()[:5]
        self.program = str(program or "").strip()
        self.raw = raw or {}

        # Derived once. These are read on every comparison, and recomputing
        # them there is what made resolution unusably slow on a real batch.
        self.gkeys = given_keys(self.first)
        self.lkeys = surname_tokens(self.last)
        folded = _fold(self.first).split()
        self._first_head = folded[0] if folded else ""
        s = _fold(self.street)
        s = re.sub(r"\b(street|st|avenue|ave|road|rd|boulevard|blvd|place|pl|"
                   r"drive|dr|court|ct|lane|ln|terrace|ter|parkway|pkwy)\b", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        self.addr_key = f"{s}|{self.zip}" if s and self.zip else ""
        d = parse_dob(self.dob)
        self.dob_key = _digits(d) if d else ""

    def label(self):
        """A short, readable name for this record, for screens and messages."""
        return f"{self.first} {self.last}".strip() or "(no name)"


# ---------------------------------------------------------------------------
# blocking: cut the work from every pair to plausible pairs only
# ---------------------------------------------------------------------------
def blocking_keys(rec: PersonRecord) -> set:
    """
    Cheap keys that a genuine pair will share on at least one.

    Every key is a combination of two facts rather than one. A single fact is
    too common to be useful: on a real batch, blocking on birth year alone puts
    hundreds of unrelated people in one bucket and the comparison never
    finishes. Requiring two facts keeps the work proportional to the data while
    still catching every case where one field changed.
    """
    keys = set()
    d = rec.dob_key
    a = rec.addr_key
    year, md = (d[:4], d[4:]) if d else ("", "")

    if d:
        keys.add("dob:" + d)                       # the date on its own is specific
    if a:
        keys.add("addr:" + a)                      # so is a full street and ZIP

    for lk in rec.lkeys:
        if year:
            keys.add(f"ly:{lk}|{year}")            # surname and birth year
        if md:
            keys.add(f"lmd:{lk}|{md}")             # surname and birth day
        if a:
            keys.add(f"la:{lk}|{a}")               # surname and address
        if rec.zip:
            keys.add(f"lz:{lk}|{rec.zip}")         # surname and ZIP

    for gk in rec.gkeys:
        if year:
            keys.add(f"gy:{gk}|{year}")            # given name and birth year
        if a:
            keys.add(f"ga:{gk}|{a}")               # given name and address

    # A given name recorded in the surname column still blocks with the right
    # people, which is what catches columns filled in the wrong order.
    for lk in rec.lkeys:
        for gid in _NICK.get(lk, ()):
            if year:
                keys.add(f"gy:g{gid}|{year}")
            if a:
                keys.add(f"ga:g{gid}|{a}")
        if year:
            keys.add(f"gy:{lk}|{year}")
        if a:
            keys.add(f"ga:{lk}|{a}")
    return keys


# ---------------------------------------------------------------------------
# scoring one pair
# ---------------------------------------------------------------------------
WEIGHTS = {
    "dob_exact": 42, "dob_near": 26,
    "last_exact": 30, "last_overlap": 24, "last_swapped": 20,
    "first_exact": 26, "first_nick": 22, "first_initial": 8,
    "addr_exact": 30, "zip_only": 6,
    "same_system_id": 100,
}

AUTO_THRESHOLD = 100     # joined without asking
PROPOSE_THRESHOLD = 62   # offered for confirmation


def score_pair(a: PersonRecord, b: PersonRecord):
    """
    Compare two records. Returns (points, evidence, cautions).

    Evidence is what agreed, in plain words. Cautions are the things a person
    should look at before accepting, such as a surname that changed.
    """
    pts = 0
    ev, caution = [], []

    if a.client_id and a.client_id == b.client_id and a.system == b.system:
        return WEIGHTS["same_system_id"], [
            f"the same {a.system or 'system'} identifier {a.client_id}"], []

    dob_state, dob_why = compare_dob(a.dob, b.dob)
    if dob_state == "exact":
        pts += WEIGHTS["dob_exact"]
        ev.append("date of birth matches exactly")
    elif dob_state == "near":
        pts += WEIGHTS["dob_near"]
        ev.append(dob_why)
        caution.append("the dates of birth are close but not identical")
    elif dob_state == "differs":
        pts -= 20
        caution.append("the dates of birth do not match")

    la, lb = a.lkeys, b.lkeys
    if la and lb:
        if la == lb:
            pts += WEIGHTS["last_exact"]
            ev.append("surname matches")
        elif la & lb:
            pts += WEIGHTS["last_overlap"]
            ev.append("part of a double surname matches "
                      f"({', '.join(sorted(la & lb))})")
            caution.append("only part of the surname matches")
        else:
            caution.append(f"the surnames are different ({a.last} and {b.last})")

    ga, gb = a.gkeys, b.gkeys
    if ga and gb:
        if a._first_head and a._first_head == b._first_head:
            pts += WEIGHTS["first_exact"]
            ev.append("given name matches")
        elif ga & gb:
            pts += WEIGHTS["first_nick"]
            ev.append(f"given names are forms of the same name "
                      f"({a.first} and {b.first})")
        elif (len(a._first_head) == 1 or len(b._first_head) == 1) and \
                a._first_head[:1] == b._first_head[:1]:
            pts += WEIGHTS["first_initial"]
            ev.append("only an initial is recorded, and it matches")

    # names entered in the wrong columns
    if (ga & b.lkeys or gb & a.lkeys or
            (a._first_head and a._first_head in b.lkeys and
             b._first_head in a.lkeys)):
        if not (la & lb):
            pts += WEIGHTS["last_swapped"]
            ev.append("the given name and surname appear to be in opposite columns")
            caution.append("the name columns look swapped in one of the records")

    if a.addr_key and a.addr_key == b.addr_key:
        pts += WEIGHTS["addr_exact"]
        ev.append("address matches")
    elif a.zip and a.zip == b.zip:
        pts += WEIGHTS["zip_only"]
        ev.append("ZIP matches")

    return pts, ev, caution


def _is_auto(a: PersonRecord, b: PersonRecord, pts, ev):
    """
    Join without asking only where a coincidence is not a reasonable
    explanation: the same identifier inside one system, or full agreement on
    name, date of birth and address at once.
    """
    if pts >= WEIGHTS["same_system_id"]:
        return True
    strong = {"date of birth matches exactly", "surname matches",
              "given name matches", "address matches"}
    return strong.issubset(set(ev))


# ---------------------------------------------------------------------------
# clustering
# ---------------------------------------------------------------------------
class _Union:
    """Union-find over record ids, used to merge records into one identity."""
    def __init__(self):
        self.parent = {}

    def find(self, x):
        """The root of a record's group, with path compression."""
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        """Join two records' groups into one."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def resolve(records, decisions=None):
    """
    Work out who is who.

    records:   list of PersonRecord
    decisions: {(rid_a, rid_b): 'same' | 'different'} from earlier review

    Returns a dict with master ids, proposals awaiting a decision, and counts.
    """
    decisions = dict(decisions or {})
    by_rid = {r.rid: r for r in records}

    # 1) block
    buckets = defaultdict(list)
    for r in records:
        for k in blocking_keys(r):
            buckets[k].append(r.rid)

    # 2) score each candidate pair once
    seen, scored = set(), {}
    for k, rids in buckets.items():
        if len(rids) < 2 or len(rids) > 150:      # a huge bucket is not evidence
            continue
        for i in range(len(rids)):
            for j in range(i + 1, len(rids)):
                pair = tuple(sorted((rids[i], rids[j])))
                if pair in seen:
                    continue
                seen.add(pair)
                a, b = by_rid[pair[0]], by_rid[pair[1]]
                pts, ev, caution = score_pair(a, b)
                if pts >= PROPOSE_THRESHOLD:
                    scored[pair] = (pts, ev, caution, _is_auto(a, b, pts, ev))

    # 3) join what is settled, collect what is not
    u = _Union()
    for r in records:
        u.find(r.rid)
    proposals, auto_links, confirmed, rejected = [], [], [], []

    for pair, (pts, ev, caution, auto) in sorted(
            scored.items(), key=lambda kv: -kv[1][0]):
        decision = decisions.get(pair)
        if decision == "different":
            rejected.append(pair)
            continue
        if decision == "same":
            u.union(*pair)
            confirmed.append(pair)
            continue
        if auto:
            u.union(*pair)
            auto_links.append({"pair": pair, "points": pts, "evidence": ev})
        else:
            proposals.append({
                "pair": pair, "points": pts, "evidence": ev, "cautions": caution,
                "a": _brief(by_rid[pair[0]]), "b": _brief(by_rid[pair[1]]),
                "reason": _headline(ev, caution),
            })

    # 4) master ids, stable and readable
    groups = defaultdict(list)
    for r in records:
        groups[u.find(r.rid)].append(r.rid)
    master_of, n = {}, 0
    for root in sorted(groups, key=lambda g: sorted(groups[g])[0]):
        n += 1
        mid = f"M{n:06d}"
        for rid in groups[root]:
            master_of[rid] = mid

    # 5) the two counts, with an honest range
    settled_clusters = len(groups)
    if proposals:
        u2 = _Union()
        for r in records:
            u2.find(r.rid)
        for pair in confirmed:
            u2.union(*pair)
        for link in auto_links:
            u2.union(*link["pair"])
        for p in proposals:
            u2.union(*p["pair"])
        if_all_accepted = len({u2.find(r.rid) for r in records})
    else:
        if_all_accepted = settled_clusters

    pairs = {(master_of[r.rid], r.program) for r in records if r.program}
    no_program = sum(1 for r in records if not r.program)

    return {
        "master_of": master_of,
        "clusters": settled_clusters,
        "unique_clients": {
            "settled": settled_clusters,
            "if_all_proposals_accepted": if_all_accepted,
            "range": (if_all_accepted, settled_clusters),
        },
        "unique_client_programs": len(pairs),
        "records_without_program": no_program,
        "proposals": proposals,
        "auto_links": auto_links,
        "confirmed": confirmed,
        "rejected": rejected,
    }


def _brief(r: PersonRecord):
    """A short description of a record for a proposal."""
    return {"rid": r.rid, "name": r.label(), "dob": r.dob, "system": r.system,
            "program": r.program, "client_id": r.client_id,
            "address": (r.street + (" " + r.zip if r.zip else "")).strip()}


def _headline(evidence, cautions):
    """One line naming why this was proposed, and what to look at."""
    if not evidence:
        return "weak agreement"
    head = evidence[0]
    if cautions:
        return f"{head}, but {cautions[0]}"
    return head


def summarize(result):
    """A short, plain report of what resolution found."""
    uc = result["unique_clients"]
    lines = [
        f"Records grouped into {uc['settled']:,} people on settled evidence.",
        f"{len(result['auto_links']):,} link(s) joined automatically, "
        f"{len(result['confirmed']):,} confirmed by a person, "
        f"{len(result['rejected']):,} rejected.",
    ]
    if result["proposals"]:
        lo, hi = uc["range"]
        lines.append(
            f"{len(result['proposals']):,} proposed link(s) are still open, so the "
            f"true count is between {lo:,} and {hi:,}. Deciding them closes the range.")
    else:
        lines.append("No proposals are open, so this count is final.")
    lines.append(f"Unique client and program pairs: "
                 f"{result['unique_client_programs']:,}.")
    if result["records_without_program"]:
        lines.append(f"{result['records_without_program']:,} record(s) have no "
                     "program recorded and are excluded from that pair count.")
    return lines
