"""H16 wording lint: no em dash, emoji or British spelling in copy text and the scanned docs, and no exclamation mark in copy text.
The exclamation check skips docs, since code samples there use comparison operators."""
import pytest

from tests.conftest import ROOT
from tests.copy.lint import EM_DASH, all_copy_texts, british_words, problems, scanned_docs

REGISTRY_FILES = [ROOT / "wholecount" / "copy" / "en.toml", ROOT / "wholecount" / "copy" / "problems.toml",
                  ROOT / "wholecount" / "copy" / "reasons.toml"]
WORDS = british_words()


def test_spelling_list_has_the_starter_words():
    assert 15 <= len(WORDS) <= 30
    assert len(WORDS) == len(set(WORDS))


@pytest.mark.parametrize("key,text", all_copy_texts(REGISTRY_FILES))
def test_copy_text_wording(key, text):
    assert problems(text, WORDS, check_exclamation=True) == [], key


@pytest.mark.parametrize("path", scanned_docs(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_doc_wording(path):
    assert problems(path.read_text(encoding="utf-8"), WORDS, check_exclamation=False) == []


def test_scanned_docs_include_milestones_and_test_docs():
    rels = {p.relative_to(ROOT).as_posix() for p in scanned_docs()}
    assert "docs/milestones/M00-foundation.md" in rels
    assert "tests/HARD_RULES.md" in rels and "tests/audit/INDEX.md" in rels


def test_negative_controls_on_a_temp_registry(tmp_path):
    british = WORDS[0]
    reg = tmp_path / "en.toml"
    reg.write_text(
        "[bad.dash]\n" f'text = "Rows {EM_DASH} counted."\n'
        "[bad.emoji]\n" 'text = "Done \U0001F389"\n'
        "[bad.zwj]\n" 'text = "a‍b"\n'
        "[bad.bang]\n" 'text = "Done!"\n'
        "[bad.spelling]\n" f'text = "The {british.upper()} is set."\n'
        "[good.plain]\n" 'text = "Nothing leaves this computer."\n',
        encoding="utf-8",
    )
    found = {k: problems(t, WORDS, check_exclamation=True) for k, t in all_copy_texts([reg])}
    assert found == {
        "bad.dash": ["em dash"], "bad.emoji": ["emoji"], "bad.zwj": ["emoji"], "bad.bang": ["exclamation mark"],
        "bad.spelling": [f"spelling: {british.upper()}"], "good.plain": [],
    }


def test_spelling_matches_whole_words_only():
    british = WORDS[0]
    assert problems(f"x{british}x and {british}s", WORDS, check_exclamation=False) == []


def test_problems_toml_reasons_are_linted(tmp_path):
    reg = tmp_path / "problems.toml"
    reg.write_text('[zip_missing]\ntitle = "No ZIP!"\nmeans = "ok"\ncheck = "ok"\nexcel = "ok"\n')
    found = {k: problems(t, WORDS, check_exclamation=True) for k, t in all_copy_texts([reg])}
    assert found["zip_missing.title"] == ["exclamation mark"]
