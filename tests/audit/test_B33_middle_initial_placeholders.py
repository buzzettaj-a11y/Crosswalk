"""B-33 (Medium): middle-initial placeholders became letters (NMI to N, Jr to J, Unknown to U)."""
import pytest

from wholecount.engine.prepare.names import middle_initial


@pytest.mark.parametrize("value", ["NMI", "NMN", "Jr", "no", "Unknown", "none", "n/a", "na", "(none)", ".", "Sr", "III", "3", "-"])
def test_B33_stop_list_gives_blank(value):
    assert middle_initial(value)[0] == ""


@pytest.mark.parametrize("value,initial", [("Marie", "M"), ("James", "J"), ("j.", "J"), ("a", "A"), ("J", "J"), ("", "")])
def test_B33_real_names_and_proof_sheet_03(value, initial):
    assert middle_initial(value)[0] == initial
