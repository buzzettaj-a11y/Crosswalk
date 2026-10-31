"""Source systems (SPEC 4.2) and source letters (SPEC 4.3).

A source system is a group of files that share one identifier space; by default each file is its own. Letters are display
only and never part of a key (SPEC 5.1).
"""
import re
from dataclasses import dataclass, replace

from wholecount.engine.letters import letter_for_index


@dataclass(frozen=True)
class SourceSystem:
    system_id: str
    display_name: str
    letters: tuple


def _stem(name):
    base = re.split(r"[\\/]", name)[-1]
    return base.rsplit(".", 1)[0] if "." in base else base


def default_systems(files):
    """files: [(letter, file name), ...] -> one system per file, named by the file name without its extension."""
    return [SourceSystem(f"system-{letter}", _stem(name), (letter,)) for letter, name in files]


def group(systems, letters):
    """Merge the systems holding these letters into the first of them. The others disappear."""
    letters = set(letters)
    members = [s for s in systems if letters & set(s.letters)]
    if len(members) < 2:
        return list(systems)
    first = members[0]
    merged = replace(first, letters=tuple(sorted({x for s in members for x in s.letters}, key=_letter_order)))
    return [merged if s is first else s for s in systems if s is first or s not in members]


def rename(systems, system_id, display_name):
    if not display_name.strip():
        raise ValueError("a system needs a name")
    return [replace(s, display_name=display_name.strip()) if s.system_id == system_id else s for s in systems]


def system_for(systems, letter):
    for s in systems:
        if letter in s.letters:
            return s
    raise KeyError(letter)


def _letter_order(letter):
    return (len(letter), letter)


class LetterBook:
    """Hands out letters in the order files are added. A file with the same fingerprint gets its letter back. A released
    letter is never handed out again in the batch."""

    def __init__(self):
        self._next = 0
        self._by_fingerprint = {}
        self._released = set()

    def assign(self, fingerprint, name=None):
        if fingerprint in self._by_fingerprint:
            return self._by_fingerprint[fingerprint]
        letter = letter_for_index(self._next)
        self._next += 1
        self._by_fingerprint[fingerprint] = letter
        return letter

    def release(self, letter):
        self._released.add(letter)
        self._by_fingerprint = {fp: x for fp, x in self._by_fingerprint.items() if x != letter}

    def issued(self):
        return self._next
