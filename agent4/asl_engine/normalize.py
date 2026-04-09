from __future__ import annotations

import re

CONTRACTIONS: dict[str, str] = {
    "don't":     "do not",
    "doesn't":   "does not",
    "didn't":    "did not",
    "can't":     "can not",
    "cannot":    "can not",
    "won't":     "will not",
    "wouldn't":  "would not",
    "couldn't":  "could not",
    "shouldn't": "should not",
    "isn't":     "is not",
    "aren't":    "are not",
    "wasn't":    "was not",
    "weren't":   "were not",
    "haven't":   "have not",
    "hasn't":    "has not",
    "hadn't":    "had not",
    "i'm":       "i am",
    "i've":      "i have",
    "i'll":      "i will",
    "i'd":       "i would",
    "you're":    "you are",
    "you've":    "you have",
    "you'll":    "you will",
    "you'd":     "you would",
    "he's":      "he is",
    "she's":     "she is",
    "it's":      "it is",
    "we're":     "we are",
    "we've":     "we have",
    "we'll":     "we will",
    "they're":   "they are",
    "they've":   "they have",
    "they'll":   "they will",
    "that's":    "that is",
    "what's":    "what is",
    "where's":   "where is",
    "who's":     "who is",
    "how's":     "how is",
    "there's":   "there is",
    "here's":    "here is",
    "let's":     "let us",
    "gonna":     "going to",
    "wanna":     "want to",
    "gotta":     "got to",
}

SLOT_RE = re.compile(r"\{(\w+)\}")


def normalize(s: str) -> str:
    """Lowercase, expand contractions, strip trailing punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = _expand_contractions(s)
    s = s.rstrip(".!?,;:")
    return " ".join(s.split())


def _expand_contractions(s: str) -> str:
    words = s.split()
    return " ".join(CONTRACTIONS.get(w, w) for w in words)


def fill_asl_template(template: str, slots: dict[str, str]) -> list[str]:
    """Replace {SLOT} markers and split into uppercase gloss tokens."""
    def _replace(m: re.Match) -> str:
        name = m.group(1)
        return slots.get(name, m.group(0)).upper()

    filled = SLOT_RE.sub(_replace, template)
    return filled.upper().split()


def build_slot_regex(pattern: str) -> tuple[re.Pattern | None, list[str]]:
    """Convert a pattern template into a compiled regex with named groups.

    Returns (None, []) if the pattern has no slots.
    """
    matches = SLOT_RE.findall(pattern)
    if not matches:
        return None, []

    names: list[str] = list(matches)

    # Replace slots with unique placeholders before normalizing
    text = pattern
    for i, name in enumerate(names):
        text = text.replace("{" + name + "}", f"__XSLOT{chr(65 + i)}__", 1)

    text = normalize(text)
    text = re.escape(text)

    # Swap placeholders for named capture groups
    for i, name in enumerate(names):
        ph = f"__xslot{chr(97 + i)}__"  # lowercased by normalize
        text = text.replace(re.escape(ph), f"(?P<{name}>.+?)", 1)

    try:
        return re.compile(f"^{text}$"), names
    except re.error:
        return None, []
