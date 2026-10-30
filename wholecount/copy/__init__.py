"""Copy registry: every user-facing sentence, with claim IDs for every claim about behavior (H11)."""

from wholecount.copy.registry import CopyError, Entry, all_entries, claims, get

__all__ = ["get", "claims", "all_entries", "Entry", "CopyError"]
