"""Summary rows (P-VAL-4, B-44). A total or heading is set aside. A surname that is a real name, like Sum, Mean or Count, makes
a summary row only when the row has no other person data."""
import re

SUMMARY_WORDS = re.compile(r"(?i)^\s*(grand\s+)?(total|subtotal|sub-total|sum|count|average|avg|mean|summary|overall|"
                           r"all\s+(clients|records|programs)|n\s*=)(?:\b|(?<==))")
NUMBERS_ONLY = re.compile(r"[\d,.\-%$ ]+")
PERSON_FIELDS = ("First_Name", "Last_Name", "Client_ID", "Address_1", "Date_of_Birth")


def _data(v):
    """A value counts as person data unless it's blank or is itself a summary word, like a Total in the ID column."""
    return bool(v.strip()) and not SUMMARY_WORDS.match(v)


def is_summary_row(values, unmapped):
    first, last = values.get("First_Name", ""), values.get("Last_Name", "")
    for name, other in ((first, last), (last, first)):
        if name and SUMMARY_WORDS.match(name):
            others = [other] + [values.get(f, "") for f in ("Client_ID", "Address_1", "Date_of_Birth")]
            if not any(_data(v) for v in others):
                return True
    if any(_data(values.get(f, "")) for f in PERSON_FIELDS):
        return False
    rest = [v for f, v in values.items() if v.strip() and f not in ("First_Name", "Last_Name")]
    rest += [v for f, v in values.items() if v.strip() and f in ("First_Name", "Last_Name", "Client_ID")]
    if unmapped.summary_word or any(SUMMARY_WORDS.match(v) for v in rest):
        return True
    numbers = [v for v in rest if NUMBERS_ONLY.fullmatch(v)]
    if unmapped.numbers_only and not [v for v in rest if not NUMBERS_ONLY.fullmatch(v)]:
        return True
    return bool(numbers) and len(numbers) == len(rest)
