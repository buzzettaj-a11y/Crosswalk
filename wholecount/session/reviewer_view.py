"""The reviewer and bulk accept rules as the window needs them, through the session layer (SPEC 8.7)."""
import tomllib
from importlib import resources

from wholecount.session.reviewer import AcceptProof, needs_second, sample_rows  # noqa: F401

_LABELS = tomllib.loads(resources.files("wholecount.copy").joinpath("reasons.toml").read_text(encoding="utf-8"))
ACCEPT_REASONS = tuple(_LABELS["accept"])
SET_ASIDE_REASONS = tuple(_LABELS["set_aside"])


def reason_label(kind, code):
    return _LABELS[kind][code]["label"]
