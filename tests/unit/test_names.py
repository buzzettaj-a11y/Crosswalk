"""names.py (P-DUP-6): folding, surname tokens, suffixes and the 92 nickname groups."""
from wholecount.engine.fold import fold
from wholecount.engine.names import given_keys, nickname_groups, same_given, suffix_of, surname_tokens, words


def test_fold_cases():
    assert fold("José Núñez") == fold("Jose Nunez")
    assert fold("O'Brien") == fold("OBrien")
    assert fold("Ana-Maria") == fold("Ana Maria")
    assert words("  Ana-Maria  O'Brien ") == "ana maria obrien"


def test_92_groups_and_bob_robert():
    assert len(nickname_groups()) == 92
    assert given_keys("Bob") & given_keys("Robert")
    assert same_given("Bob", "Robert") and same_given("José", "Jose") and not same_given("Ana", "Beth")


def test_surname_tokens():
    assert surname_tokens("Smith Jr") == {"smith"}
    assert surname_tokens("García López") == surname_tokens("Garcia-Lopez") == {"garcia", "lopez"}
    assert surname_tokens("de la Cruz") == {"cruz"}
    assert surname_tokens("Van") == {"van"}
    assert surname_tokens("A Smith") == {"smith"}


def test_suffix_of():
    assert suffix_of("Smith Jr") == "jr" and suffix_of("Smith III") == "iii" and suffix_of("Smith") == ""
    assert suffix_of("Smith", suffix_column="Sr.") == "sr"
