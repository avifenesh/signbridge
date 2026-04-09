"""Shared types for the ASL translation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TranslationMethod(Enum):
    """Which tier produced the translation."""

    HASH = "hash"
    SIMILARITY = "similarity"
    MODEL = "model"
    RULES_ONLY = "rules_only"  # Fallback: grammar rules without tier match


@dataclass
class TranslationResult:
    """Output of the ASL translation engine.

    Matches the spec API contract:
    {
      "asl_gloss": ["BOOK", "I", "GIVE-YOU"],
      "method": "hash",
      "confidence": 1.0
    }
    """

    asl_gloss: list[str]
    method: TranslationMethod
    confidence: float
    english: str = ""
    debug: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "asl_gloss": self.asl_gloss,
            "method": self.method.value,
            "confidence": round(self.confidence, 3),
        }
        if self.debug:
            d["debug"] = self.debug
        return d
