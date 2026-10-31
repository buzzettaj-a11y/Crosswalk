"""Reads the settings files in this package. Settings hold thresholds and word lists, never client data."""
import tomllib
from importlib import resources


def load(name):
    """The parsed contents of wholecount/settings/<name>.toml."""
    text = resources.files("wholecount.settings").joinpath(f"{name}.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)
