"""P-DUP-6: folding text for comparison, so José equals Jose and O'Brien equals OBrien. M06 reuses it."""
import unicodedata


def fold(text):
    """NFKD, combining marks dropped, casefolded, and only letters and digits kept."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
    return "".join(ch for ch in plain if ch.isalnum())
