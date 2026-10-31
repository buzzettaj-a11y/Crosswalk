"""SPEC 4.1: the canonical fields and their flags, custom fields, and the round trip."""
import pytest

from tests.support.mapping import profiles
from wholecount.engine.mapping import auto_map, mapping_warnings, process_blocks
from wholecount.engine.schema import FieldType, Schema, SchemaError, default_schema

S = default_schema()


def test_the_eleven_fields_in_order():
    assert [f.key for f in S.fields] == ["First_Name", "Middle_Initial", "Last_Name", "Client_ID", "Address_1", "Address_2", "City",
                                         "State", "Zip", "Program", "Date_of_Birth"]
    assert all(f.builtin for f in S.fields)


def test_flags():
    assert {f.key for f in S.fields if f.required} == {"First_Name", "Last_Name", "Client_ID"}
    assert {f.key for f in S.fields if f.required_for_mapping} == {"Address_1", "City", "State", "Zip"}
    assert S.get("Date_of_Birth").enabled and S.get("Date_of_Birth").type == FieldType.DATE
    assert S.get("Middle_Initial").max_length == 1


def test_client_id_optional_and_dob_disable():
    assert not S.with_required("Client_ID", False).get("Client_ID").required
    assert not S.with_enabled("Date_of_Birth", False).get("Date_of_Birth").enabled
    with pytest.raises(SchemaError):
        S.with_required("First_Name", False)
    with pytest.raises(SchemaError):
        S.remove_custom("Zip")


@pytest.mark.parametrize("key,reason", [("1abc", "custom_key_invalid"), ("has space", "custom_key_invalid"), ("x" * 41, "custom_key_invalid"),
                                        ("zip", "custom_key_taken"), ("first_name", "custom_key_taken")])
def test_custom_key_validation(key, reason):
    with pytest.raises(SchemaError) as e:
        S.add_custom(key)
    assert str(e.value) == reason


def test_custom_max_length_and_type():
    for bad in (0, 1001, True):
        with pytest.raises(SchemaError):
            S.add_custom("Score", max_length=bad)
    with pytest.raises(SchemaError):
        S.add_custom("Score", type="text")
    s = S.add_custom("Score", type=FieldType.WHOLE_NUMBER, max_length=1000, default="0")
    f = s.get("Score")
    assert not f.builtin and not f.needed_to_count and f.default == "0"
    with pytest.raises(SchemaError):
        s.add_custom("SCORE")


def test_round_trip():
    s = S.add_custom("Score", type=FieldType.DECIMAL, required=True, needed_to_count=True).with_enabled("Date_of_Birth", False)
    assert Schema.from_dict(s.to_dict()) == s


def test_required_custom_blocks_only_when_needed_to_count():
    p = profiles(["First Name", "Last Name", "Client ID"])
    plain = S.add_custom("Score", required=True)
    m = {"t": auto_map(plain, p, "t")}
    assert process_blocks(plain, m, (), {"t": p}) == []
    assert [(w.field, w.kind) for w in mapping_warnings(plain, m)] == [("Score", "custom_required_no_column")]
    counting = S.add_custom("Score", required=True, needed_to_count=True)
    m = {"t": auto_map(counting, p, "t")}
    assert [(b.field, b.kind) for b in process_blocks(counting, m, (), {"t": p})] == [("Score", "missing_required")]
    assert mapping_warnings(counting, m) == []
