"""Wording checks for H16, shared by the lint tests. Plain functions over text, so negative controls can feed them anything."""
import pathlib
import re

from tests.conftest import ROOT

EM_DASH = "—"
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿️‍]")
SPELLING_FILE = ROOT / "wholecount" / "copy" / "us_spelling.txt"


def british_words(path=SPELLING_FILE):
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            words.append(s.lower())
    return words


def spelling_re(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)


def problems(text, words, check_exclamation):
    """Every wording problem in one text: em dashes, emoji, British spellings and, for copy text, exclamation marks."""
    found = []
    if EM_DASH in text:
        found.append("em dash")
    if EMOJI_RE.search(text):
        found.append("emoji")
    if check_exclamation and "!" in text:
        found.append("exclamation mark")
    found += [f"spelling: {m.group(0)}" for m in spelling_re(words).finditer(text)]
    return found


def scanned_docs(root=ROOT):
    """Milestone docs and the test-folder docs the lint covers."""
    return sorted((root / "docs" / "milestones").glob("*.md")) + sorted((root / "tests").rglob("*.md"))


def all_copy_texts(registry_files):
    import tomllib

    from wholecount.copy.registry import load

    out = []
    for f in registry_files:
        text = pathlib.Path(f).read_text(encoding="utf-8")
        entries = load(text)
        out += [(e.key, e.text) for e in entries.values()]
        # problems.toml tables have title, means, check and excel rather than text
        for code, reason in tomllib.loads(text).items():
            if isinstance(reason, dict) and "text" not in reason:
                out += [(f"{code}.{k}", v) for k, v in reason.items() if isinstance(v, str)]
    return out
