"""The NYC ZIP table (P-STD-3). An explicit list, never ranges. Built by tools/make_zip_table.py from cited public sources."""
import csv
import io
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=1)
def _table():
    text = resources.files("wholecount.engine.geo").joinpath("data/nyc_zips.csv").read_text(encoding="utf-8")
    return {row["zip"]: row["borough"] for row in csv.DictReader(io.StringIO(text))}


def nyc_zips():
    """{zip: borough} for every NYC ZIP."""
    return dict(_table())


def borough_for_zip(zip_code):
    return _table().get(zip_code)


def is_nyc_zip(zip_code):
    return zip_code in _table()
