"""The address key (M05 ADDR-1 to ADDR-6, SPEC 5.1, P-GEO-3, C-24, P-ID-5)."""
from wholecount.engine.addresskey import address_key, normalize_street, split_house_street


def test_ADDR_1_fold_case_punctuation_and_hyphens():
    assert normalize_street("Ávenue  O'Brien, Jr.") == normalize_street("avenue obrien jr")
    assert normalize_street("Wilkes-Barre St") == "wilkes barre street"
    assert address_key("42-09", "Main St", "11355") == "42-09|main street|11355"
    assert address_key("42 - 09", "Main St", "11355") == "42-09|main street|11355"


def test_ADDR_2_ordinal_suffixes_drop():
    assert normalize_street("45th St") == normalize_street("45 St") == "45 street"
    assert normalize_street("E 2nd Ave") == "east 2 avenue"
    assert address_key("1", "W 101st St", "10025") == address_key("1", "W 101 St", "10025")


def test_ADDR_3_directions_and_types_expand():
    pairs = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard", "dr": "drive", "ln": "lane",
             "ct": "court", "pl": "place", "ter": "terrace", "pkwy": "parkway", "hwy": "highway", "sq": "square", "cir": "circle",
             "expy": "expressway", "plz": "plaza"}
    for short, full in pairs.items():
        assert normalize_street(f"Oak {short}") == f"oak {full}"
    assert normalize_street("N Oak St") == "north oak street"
    assert normalize_street("S Oak St") == "south oak street"
    assert normalize_street("E Oak St") == "east oak street"
    assert normalize_street("W Oak St") == "west oak street"


def test_ADDR_4_st_is_saint_unless_last():
    assert normalize_street("St Marks Pl") == "saint marks place"
    assert normalize_street("St Nicholas Ave") == "saint nicholas avenue"
    assert normalize_street("Main St") == "main street"


def test_ADDR_5_type_stays_and_spelled_ordinals_do_not_convert():
    assert address_key("45", "Park Ave", "10016") != address_key("45", "Park Pl", "10016")
    assert address_key("100", "W 45th St", "10036") == address_key("100", "West 45th Street", "10036")
    assert address_key("123", "Fulton St", "11201") != address_key("123", "Fulton Ave", "11201")
    assert normalize_street("Fifth Avenue") == "fifth avenue" != normalize_street("5 Ave")


def test_ADDR_6_units_are_never_in_the_key():
    assert split_house_street("123 Main St") == ("123", "Main St")
    assert split_house_street("Main St") == ("", "")
    assert address_key("123", "Main St", "") == "123|main street|-"
    assert "apt" not in address_key(*split_house_street("123 Main St"), "11201")
