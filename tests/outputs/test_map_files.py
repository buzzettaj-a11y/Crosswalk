"""Map_Counts and Map_Points (P-GEO-6, P-GEO-7): small cells blanked, no person fields, one moved point per building."""
import pytest

from tests.fixtures.outputs.fixture import session
from tests.support.files_run import run, write_csv
from tests.support.outputs import header, read, write
from wholecount import copy
from wholecount.engine.geo.offset import haversine_ft


@pytest.mark.claim("CL-OUT-07")
def test_counts_points_and_coordinates(tmp_path):
    s = session(tmp_path)
    write(s, tmp_path / "plain")
    assert not (tmp_path / "plain" / "Map_Points.csv").exists()
    assert "Latitude" not in header(tmp_path / "plain" / "Final_Clean_Mapped.csv")
    counts = read(tmp_path / "plain" / "Map_Counts.csv")
    assert counts and all(r["Count"] == copy.get("map.fewer_than", limit=11) for r in counts)
    receipt = write(s, tmp_path / "full", map_points=True, exact_coordinates=True)
    assert "Latitude" in header(tmp_path / "full" / "Final_Clean_Mapped.csv")
    assert header(tmp_path / "full" / "Map_Points.csv") == ["Program", "Latitude", "Longitude"]
    from wholecount.engine.outputs.receipt import receipt_text
    assert copy.get("outputs.note.exact_coordinates") in receipt_text(receipt)
    clean = read(tmp_path / "full" / "Final_Clean_Mapped.csv")
    assert all(r["Senate_District"] == "26" for r in clean if r["Location_Status"].startswith("Mapped"))


def test_300_clients_at_one_door(tmp_path):
    from tests.fixtures.outputs.fixture import districts
    from tests.fixtures.session import r_fixture
    rows = [[f"D{i:04d}", f"Given{i}", f"Family{i}", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"] for i in range(300)]
    cols = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
    s = run(tmp_path, [write_csv(tmp_path / "in" / "door.csv", cols, rows)], districts=districts(tmp_path), backend=r_fixture.reference())
    write(s, tmp_path / "o", map_points=True)
    pts = read(tmp_path / "o" / "Map_Points.csv")
    assert len(pts) == 300 and len({(p["Latitude"], p["Longitude"]) for p in pts}) == 1
    lat, lon = float(pts[0]["Latitude"]), float(pts[0]["Longitude"])
    door = r_fixture.GAZETTEER[0]
    assert 149.5 <= haversine_ft(door[4], door[5], lat, lon) <= 250.5
    write(s, tmp_path / "o2", map_points=True)
    assert read(tmp_path / "o2" / "Map_Points.csv") == pts
