"""Fixture builders for M06: person rows and copy rows from short literal records, keyed with the test secret."""
from tests.support.secrets import TEST_SECRET
from wholecount.engine.addresskey import address_key, split_house_street
from wholecount.engine.copies import CopyRow, details_signature
from wholecount.engine.fold import fold
from wholecount.engine.identity import PersonRow
from wholecount.session.keys import person_key
from wholecount.session.secret_store import InstallSecret

SECRET = InstallSecret(TEST_SECRET)


def addr(street_line, zip5):
    house, street = split_house_street(street_line)
    return address_key(house, street, zip5) if house else ""


def key_for(system, client_id, first, last, dob, akey, mode=None, record_key=""):
    """The person key M08 will build: default (Client_ID when there is one), details (no Client_ID), or row."""
    if mode == "row":
        return person_key(SECRET, "row", client_id=record_key)
    if client_id and mode != "details":
        return person_key(SECRET, system, client_id=client_id)
    return person_key(SECRET, system, given=fold(first), surname=fold(last), dob=dob or None, address_key=akey)


def prow(record_key, system, client_id, first, last, dob="", street="", zip5="", unit="", program="", mode=None):
    akey = addr(street, zip5) if street else ""
    return PersonRow(record_key, key_for(system, client_id, first, last, dob, akey, mode, record_key), system, client_id, first,
                     last, dob, akey, unit, zip5, program)


def crow(record_key, table, system, client_id, first, last, dob="", street="", zip5="", program="", middle="", **extra):
    akey = addr(street, zip5) if street else ""
    values = (("Client_ID", client_id), ("First_Name", first), ("Middle_Initial", middle), ("Last_Name", last),
              ("Date_of_Birth", dob), ("Address_1", street), ("Zip", zip5), ("Program", program)) + tuple(sorted(extra.items()))
    return CopyRow(record_key, table, system, client_id, first, middle, last, dob, akey, program, values)


def to_person(c, modes=None):
    """A CopyRow as the PersonRow M08 would pass to resolve, keyed with key_modes' answer."""
    mode = (modes or {}).get(c.record_key)
    return PersonRow(c.record_key, key_for(c.system, c.client_id, c.first, c.last, c.dob, c.address_key, mode, c.record_key),
                     c.system, c.client_id, c.first, c.last, c.dob, c.address_key, "", (dict(c.values).get("Zip") or ""),
                     c.program)


C01_A = [("A1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "10451"),
         ("A2", "Jordan", "Smith", "2015-06-01", "10 Oak St", "11201"),
         ("A3", "Robert", "Smith", "1962-03-14", "20 Elm St", "11201"),
         ("A4", "Ana", "Perez", "1990-05-06", "7 Elm St", "10013"),
         ("A5", "Luis", "Diaz", "1980-02-02", "123 45th St", "11377"),
         ("A6", "Carlos", "Vega", "1975-01-01", "5 A St", "10001")]
C01_B = [("B1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "10451"),
         ("B2", "Jaden", "Smith", "2015-06-01", "10 Oak St", "11201"),
         ("B3", "Robert", "Smith Jr", "1992-03-14", "20 Elm St", "11201"),
         ("B4", "Ana", "Perez", "1990-06-05", "7 Elm St", "10013"),
         ("B5", "Luis", "Diaz", "1980-02-02", "123 45th Ave", "11377"),
         ("B6", "Elena", "Vega", "1999-09-09", "6 B St", "10001")]


def c01_rows():
    """The 12 records of docs/audit/C-scripts/fixtures.py: files A and B are two systems with their own Client_IDs."""
    out = []
    for system, recs in (("A", C01_A), ("B", C01_B)):
        for cid, first, last, dob, street, zip5 in recs:
            out.append(prow(cid, system, cid, first, last, dob, street, zip5, program="Housing"))
    return out


def by_record(rows):
    return {r.record_key: r.person_key for r in rows}


def pair_of(rows, a, b):
    k = by_record(rows)
    return tuple(sorted((k[a], k[b])))


__all__ = ["prow", "crow", "to_person", "c01_rows", "by_record", "pair_of", "addr", "key_for", "details_signature", "SECRET"]
