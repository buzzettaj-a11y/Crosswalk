"""The theme: tokens to QSS, the bundled Archivo font, and the text and background pairs the contrast test checks."""
import json
import pathlib
from functools import lru_cache

HERE = pathlib.Path(__file__).resolve().parent


def resource_path(*parts):
    """The one helper that finds a bundled file. M14 points it at the bundle."""
    return HERE.joinpath(*parts)


@lru_cache(maxsize=1)
def tokens():
    return json.loads(resource_path("tokens.json").read_text(encoding="utf-8"))


def color(name):
    return {t["name"]: t["value"] for t in tokens()["color"]["tokens"]}[name]


# Every text color on every background the frame uses (SPEC 11.2). The contrast test checks each pair.
TEXT_PAIRS = (
    ("ink", "bg-card"), ("ink", "bg-page"), ("ink", "bg-surface"), ("ink-2", "bg-card"), ("ink-2", "bg-surface"),
    ("muted", "bg-card"), ("muted", "bg-page"), ("muted", "bg-surface"), ("blue-700", "blue-100"), ("blue-700", "bg-card"),
    ("blue-500", "bg-card"), ("blue-500", "bg-surface"), ("green-700", "green-100"), ("green-700", "bg-card"),
    ("amber-700", "amber-100"), ("amber-700", "bg-card"), ("amber-700", "bg-surface"), ("on-dark", "ink"),
    ("on-dark-muted", "ink"), ("#ffffff", "blue-500"), ("#ffffff", "amber-500"), ("#ffffff", "green-500"),
)
