"""Source letters (SPEC 4.3). Display only: no key ever includes a letter."""


def letter_for_index(i):
    """0 is A, 25 is Z, 26 is AA, then AB and on, as spreadsheet columns are named."""
    if i < 0:
        raise ValueError("index must be 0 or more")
    n, out = i + 1, ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out
