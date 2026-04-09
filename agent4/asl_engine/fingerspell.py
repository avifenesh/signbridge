from .types import SignEntry, SignType


def fingerspell(word: str) -> SignEntry:
    """Convert a word into a fingerspelled SignEntry (A-Z, 0-9)."""
    upper = word.strip().upper()
    letters = [c for c in upper if c.isalpha() or c.isdigit()]
    if not letters:
        letters = [upper]
    return SignEntry(
        gloss=upper,
        type=SignType.FINGERSPELL,
        duration_ms=len(letters) * 300,
        letters=letters,
    )
