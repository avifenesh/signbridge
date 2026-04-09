"""ASL Translation Engine — 3-tier cascade orchestrator.

Translates English sentences to ASL gloss sequences by trying each tier
in order: hash table → vector similarity → model. Falls back to
grammar rules if all tiers miss.
"""

from __future__ import annotations

from translation.config import TIER2_MIN_CONFIDENCE
from translation.gloss.rules import apply_rules
from translation.tier1.hash_table import HashTable
from translation.types import TranslationMethod, TranslationResult


class TranslationEngine:
    """Orchestrates the 3-tier ASL translation cascade."""

    def __init__(self):
        self.tier1 = HashTable()
        self._tier2 = None
        self._tier3 = None

    @property
    def tier2(self):
        if self._tier2 is None:
            from translation.tier2.similarity import SimilaritySearch
            self._tier2 = SimilaritySearch()
        return self._tier2

    @property
    def tier3(self):
        if self._tier3 is None:
            from translation.tier3.model import GlossModel
            self._tier3 = GlossModel()
        return self._tier3

    def translate(self, sentence: str) -> TranslationResult:
        """Translate an English sentence to ASL gloss.

        Cascade:
        1. Tier 1 (hash): exact match or pattern → confidence 0.95-1.0
        2. Tier 2 (similarity): vector match → confidence varies
        3. Tier 3 (model): seq2seq inference → confidence varies
        4. Fallback: rule-based grammar transformation

        Always returns a result — the fallback is guaranteed.
        """
        # Tier 1: Hash table (instant)
        result = self.tier1.translate(sentence)
        if result:
            return result

        # Tier 2: Vector similarity (fast, requires numpy/faiss)
        try:
            result = self.tier2.translate(sentence)
            if result and result.confidence >= TIER2_MIN_CONFIDENCE:
                return result
        except Exception:
            pass  # numpy/faiss not installed — skip tier 2

        # Tier 3: Model (slower, may not be available)
        try:
            result = self.tier3.translate(sentence)
            if result:
                return result
        except Exception:
            pass  # onnxruntime not installed — skip tier 3

        # Fallback: grammar rules
        gloss = apply_rules(sentence)
        return TranslationResult(
            asl_gloss=gloss,
            method=TranslationMethod.RULES_ONLY,
            confidence=0.3,
            english=sentence,
            debug={"note": "All tiers missed. Used rule-based fallback."},
        )

    def stats(self) -> dict:
        """Return engine status."""
        result = {"tier1": self.tier1.stats}
        try:
            result["tier2"] = {"index_size": self.tier2.index_size}
        except Exception:
            result["tier2"] = {"index_size": 0, "status": "unavailable (numpy/faiss not installed)"}
        try:
            result["tier3"] = self.tier3.stats
        except Exception:
            result["tier3"] = {"status": "unavailable (onnxruntime not installed)"}
        return result
