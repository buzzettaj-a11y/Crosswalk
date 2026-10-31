"""tools/screens.py (M10 section 17): every frame the milestone lists, rendered the same way twice."""
from tools import screens


def test_frames_cover_the_milestone_list():
    names = {n for n, _, _ in screens.frames()}
    for s in ("01-sources", "07-review", "09-export"):
        assert {f"{s}-1440.png", f"{s}-1280.png"} <= names
    assert {"running-1440.png", "running-1280.png", "after-medium-log-1440.png", "low-1440.png", "stale-1440.png",
            "practice-1440.png", "held-1440.png", "drawer-details-1280.png", "drawer-yourdata-1440.png",
            "drawer-check-1440.png"} <= names
    assert set(screens.COMMITTED) <= names


def test_render_is_deterministic(tmp_path, qapp):
    a = screens.render({"running-1280.png", "07-review-1440.png"}, tmp_path / "a")
    b = screens.render({"running-1280.png", "07-review-1440.png"}, tmp_path / "b")
    assert [p.name for p in a] == [p.name for p in b] and len(a) == 2
    for x, y in zip(a, b):
        assert x.read_bytes() == y.read_bytes()


def test_committed_frames_exist():
    for name in screens.COMMITTED:
        assert (screens.COMMIT / name).is_file()
