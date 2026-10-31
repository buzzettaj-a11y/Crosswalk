"""B-22 (High): Program was mapped to a date column, and Program ID became the Client ID."""
from tests.support.mapping import mapped, profiles
from wholecount.engine.mapping import auto_map, process_blocks
from wholecount.engine.schema import default_schema

BASE = ["First Name", "Last Name", "Client ID", "Address", "City", "State", "Zip"]


def test_B22_program_start_date_never_maps():
    m = mapped(BASE + ["Program Start Date"], {"Program Start Date": ["03/04/2024"] * 5})
    assert "Program" not in m.as_names()


def test_B22_program_column_holding_dates_is_rejected_by_values():
    m = mapped(BASE + ["Program"], {"Program": ["03/04/2024", "1/15/2023", "2024-02-01", "12.01.2022", "Youth"]})
    assert "Program" not in m.as_names()


def test_B22_service_date_never_maps_and_service_provider_is_not_a_program():
    for cols in (BASE + ["Service Date", "Service Provider"], BASE + ["Service Provider", "Service Date"]):
        assert "Program" not in mapped(cols, {"Service Date": ["03/04/2024"] * 3}).as_names()


def test_B22_program_id_fills_neither_role_and_blocks_once():
    schema = default_schema()
    cols = ["First Name", "Last Name", "Program ID", "Address", "City", "State", "Zip"]
    p = profiles(cols)
    m = auto_map(schema, p, "t")
    names = m.as_names()
    assert "Client_ID" not in names and "Program" not in names
    assert len(set(names.values())) == len(names)
    blocks = process_blocks(schema, {"t": m}, (), {"t": p})
    assert [(b.field, b.kind, b.also) for b in blocks] == [("Client_ID", "missing_required", "Date_of_Birth")]
