"""Keys (SPEC 5.1). Every key that involves client data is an HMAC-SHA256 with the install secret.

Letters and block ranges are display only and never part of a key, so add order and added rows never change a key.
"""
import hashlib
import hmac
import re

SEP = "\x1f"
_PUNCT = re.compile(r"[\W_]+", re.UNICODE)


def _secret_bytes(secret):
    # The one place a secret's bytes are read.
    return secret._value


def normalize_file_name(name):
    """Lowercase, no folder, each run of spaces and punctuation one underscore, ends trimmed. The extension stays."""
    base = re.split(r"[\\/]", name)[-1]
    return _PUNCT.sub("_", base.lower()).strip("_")


def source_fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def header_signature(cells):
    return hashlib.sha256(SEP.join(cells).encode("utf-8")).hexdigest()[:8]


def file_keys(files):
    """[(name, fingerprint), ...] in add order -> [file key or None]. None marks a duplicate_file: the same name and the same
    fingerprint as an earlier file. The second and later files with one normalized name get ~ and 6 hex of their fingerprint."""
    seen_names, seen_pairs, out = set(), set(), []
    for name, fp in files:
        norm = normalize_file_name(name)
        if (norm, fp) in seen_pairs:
            out.append(None)
            continue
        seen_pairs.add((norm, fp))
        out.append(f"{norm}~{fp[:6]}" if norm in seen_names else norm)
        seen_names.add(norm)
    return out


def table_key(file_key, sheet, signature, ordinal=1):
    sheet_part = sheet if sheet else "data"
    if ordinal > 1:
        sheet_part = f"{sheet_part} #{ordinal}"
    return f"{file_key} :: {sheet_part} :: {signature}"


def record_keys(secret, table_key_, rows):
    """First 20 hex of HMAC-SHA256 over the table key, the row's cleaned cell texts and its occurrence number, joined with U+001F.
    The occurrence counts exact-duplicate rows in order within the table, ticked or not."""
    key = _secret_bytes(secret)
    seen, out = {}, []
    for cells in rows:
        t = tuple(cells)
        n = seen.get(t, 0)
        seen[t] = n + 1
        msg = SEP.join([table_key_, *cells, str(n)]).encode("utf-8")
        out.append(hmac.new(key, msg, hashlib.sha256).hexdigest()[:20])
    return out


def person_key(secret, system, client_id=None, given=None, surname=None, dob=None, address_key=None):
    """Full HMAC-SHA256 hex. With a Client_ID: system, client_id. Without: system, given, surname, dob. With no dob either:
    system, given, surname, an empty dob slot, address_key. The caller passes folded names and the address key."""
    system = system.strip().lower()
    client_id = (client_id or "").strip()
    if client_id:
        parts = [system, client_id]
    elif dob:
        parts = [system, given or "", surname or "", dob]
    else:
        parts = [system, given or "", surname or "", "", address_key or ""]
    return hmac.new(_secret_bytes(secret), SEP.join(parts).encode("utf-8"), hashlib.sha256).hexdigest()
