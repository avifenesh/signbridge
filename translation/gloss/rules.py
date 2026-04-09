"""English → ASL gloss grammar transformation rules.

ASL has its own grammar distinct from English:
  - Topic-comment structure: topic comes first ("BOOK, I GIVE-YOU")
  - WH-questions end with the question word ("YOUR NAME WHAT")
  - Negation typically follows the verb ("UNDERSTAND I NOT")
  - Time references come first ("YESTERDAY I GO STORE")
  - Adjectives follow nouns ("CAR RED")
  - No copula ("be" is dropped)
  - No articles (a, an, the are dropped)
  - Directional verbs incorporate subject/object ("GIVE-YOU" not "GIVE TO YOU")

This module applies rule-based transformations as a best-effort fallback
and as a post-processing step for tier 1/2 template outputs.
"""

from __future__ import annotations

import re

# Words to drop entirely (articles, copulas, filler)
_DROP_WORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been", "being",
    "do", "does", "did",  # as auxiliaries, not main verbs
    "to",  # infinitive marker
    "it",  # expletive "it" (e.g., "it is raining")
    "very", "really", "just", "quite",
}

# Pronouns → ASL gloss
_PRONOUN_MAP = {
    "i": "I",
    "me": "I",
    "my": "MY",
    "mine": "MY",
    "myself": "I",
    "you": "YOU",
    "your": "YOUR",
    "yours": "YOUR",
    "yourself": "YOU",
    "he": "HE",
    "him": "HE",
    "his": "HIS",
    "she": "SHE",
    "her": "HER",
    "hers": "HER",
    "we": "WE",
    "us": "WE",
    "our": "OUR",
    "they": "THEY",
    "them": "THEY",
    "their": "THEIR",
    "this": "THIS",
    "that": "THAT",
    "these": "THESE",
    "those": "THOSE",
}

# Common contractions → expanded forms
_CONTRACTIONS = {
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "i'd": "i would",
    "you're": "you are",
    "you've": "you have",
    "you'll": "you will",
    "you'd": "you would",
    "he's": "he is",
    "she's": "she is",
    "it's": "it is",
    "we're": "we are",
    "we've": "we have",
    "we'll": "we will",
    "they're": "they are",
    "they've": "they have",
    "they'll": "they will",
    "that's": "that is",
    "there's": "there is",
    "here's": "here is",
    "what's": "what is",
    "who's": "who is",
    "where's": "where is",
    "how's": "how is",
    "can't": "can not",
    "won't": "will not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
    "wouldn't": "would not",
    "couldn't": "could not",
    "shouldn't": "should not",
    "let's": "let us",
}

# Negation words
_NEGATION_WORDS = {"not", "no", "never", "nothing", "nobody", "nowhere", "neither", "nor"}

# WH-question words
_WH_WORDS = {"what", "who", "where", "when", "why", "how", "which", "whom", "whose"}

# Time words that should move to front in ASL
_TIME_WORDS = {
    "yesterday", "today", "tomorrow", "now", "later", "before", "after",
    "already", "recently", "soon", "always", "sometimes", "often", "never",
    "morning", "afternoon", "evening", "night", "last", "next", "every",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}

# Directional verbs — these incorporate subject/object in ASL
_DIRECTIONAL_VERBS = {
    "give": "GIVE",
    "tell": "TELL",
    "ask": "ASK",
    "show": "SHOW",
    "send": "SEND",
    "pay": "PAY",
    "help": "HELP",
    "teach": "TEACH",
    "invite": "INVITE",
}


def expand_contractions(text: str) -> str:
    """Expand English contractions."""
    words = text.lower().split()
    expanded = []
    for word in words:
        clean = word.strip(".,!?;:")
        if clean in _CONTRACTIONS:
            expanded.extend(_CONTRACTIONS[clean].split())
        else:
            expanded.append(clean)
    return " ".join(expanded)


def tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, strip punctuation, split."""
    text = text.lower()
    text = re.sub(r"[^\w\s'-]", "", text)
    return text.split()


def apply_rules(english: str) -> list[str]:
    """Apply ASL grammar rules to transform English into ASL gloss order.

    This is a rule-based approximation. It handles:
    1. Contraction expansion
    2. Drop articles, copulas, filler
    3. Move time references to front
    4. Move WH-words to end (for questions)
    5. Move negation after verb
    6. Map pronouns to ASL gloss
    7. Uppercase all remaining words as gloss tokens

    Returns:
        List of ASL gloss tokens.
    """
    # Expand contractions first
    text = expand_contractions(english)
    tokens = tokenize(text)

    if not tokens:
        return []

    # Separate components
    time_tokens = []
    wh_tokens = []
    negation_tokens = []
    content_tokens = []

    i = 0
    while i < len(tokens):
        word = tokens[i]

        # Drop articles and copulas
        if word in _DROP_WORDS:
            i += 1
            continue

        # Collect time references
        if word in _TIME_WORDS:
            time_tokens.append(word.upper())
            i += 1
            continue

        # Collect WH-words
        if word in _WH_WORDS:
            wh_tokens.append(word.upper())
            i += 1
            continue

        # Collect negation
        if word in _NEGATION_WORDS:
            negation_tokens.append("NOT" if word == "not" else word.upper())
            i += 1
            continue

        # Map pronouns
        if word in _PRONOUN_MAP:
            content_tokens.append(_PRONOUN_MAP[word])
            i += 1
            continue

        # Directional verbs: try to capture "give you" → "GIVE-YOU"
        if word in _DIRECTIONAL_VERBS and i + 1 < len(tokens):
            next_word = tokens[i + 1]
            if next_word in _PRONOUN_MAP:
                target = _PRONOUN_MAP[next_word]
                content_tokens.append(f"{_DIRECTIONAL_VERBS[word]}-{target}")
                i += 2
                continue

        # Default: uppercase as gloss token
        content_tokens.append(word.upper())
        i += 1

    # ASL word order: TIME + TOPIC/CONTENT + NEGATION + WH-QUESTION
    gloss = time_tokens + content_tokens + negation_tokens + wh_tokens

    return gloss if gloss else [english.upper()]
