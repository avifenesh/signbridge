"""
Tier 2: Query the FAISS index at inference time (Python-side).

Mirrors the logic that will run on Android via ONNX Runtime + FAISS Android port.
Used for:
  - Offline evaluation of the vector tier
  - Contract test validation
  - Building the export pipeline

Slot adaptation:
  When the nearest-neighbor match comes from a pattern with {SLOT} placeholders,
  we attempt to re-apply the source pattern's regex to the query sentence to
  extract slot values. If extraction succeeds, we fill the ASL template.
  If it fails, we fall back to using the stored ASL gloss directly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from translation.config import (
    FAISS_INDEX,
    INDEX_MAP_JSON,
    MODEL_CACHE,
    VECTOR_CONFIDENCE_THRESHOLD,
)
from translation.tier2.embed import MiniLMEmbedder


@dataclass
class VectorMatch:
    asl_gloss: str          # ASL gloss tokens string (space-separated)
    source_english: str     # the matched corpus sentence
    source_pattern: str     # the source Tier 1 pattern ("i want {THING}" etc.)
    cosine_similarity: float
    method: str = "vector_similarity"

    @property
    def gloss_tokens(self) -> list[str]:
        return self.asl_gloss.split()

    @property
    def confidence(self) -> float:
        return self.cosine_similarity


class VectorIndex:
    """Runtime FAISS index for Tier 2 ASL translation."""

    def __init__(
        self,
        index_path: Path = FAISS_INDEX,
        map_path: Path = INDEX_MAP_JSON,
        threshold: float = VECTOR_CONFIDENCE_THRESHOLD,
        model_cache: Path | None = MODEL_CACHE,
    ) -> None:
        self.index_path = index_path
        self.map_path = map_path
        self.threshold = threshold
        self._index = None
        self._mapping: list[dict] = []
        self._embedder = MiniLMEmbedder(model_cache=model_cache)
        self._loaded = False

    def load(self) -> "VectorIndex":
        try:
            import faiss
        except ImportError as e:
            raise ImportError("faiss-cpu not installed") from e

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {self.index_path}. "
                "Run: python -m translation.tier2.build_index"
            )

        self._index = faiss.read_index(str(self.index_path))
        with open(self.map_path, encoding="utf-8") as f:
            self._mapping = json.load(f)

        self._embedder.load()
        self._loaded = True
        return self

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def query(self, sentence: str, top_k: int = 3) -> VectorMatch | None:
        """
        Find nearest ASL match for an English sentence.

        Returns None if best cosine similarity is below threshold.
        Applies slot adaptation when the matched pattern has {SLOT} placeholders.
        """
        if not self._loaded:
            raise RuntimeError("Call load() before query()")

        vec = self._embedder.embed_one(sentence.lower()).reshape(1, -1)
        distances, indices = self._index.search(vec, top_k)

        best_dist = float(distances[0][0])
        best_idx = int(indices[0][0])

        if best_dist < self.threshold:
            return None

        entry = self._mapping[best_idx]
        asl = entry["asl"]
        pattern = entry["pattern"]

        # Attempt slot adaptation if the source pattern has slots
        adapted = _adapt_slots(sentence.lower(), pattern, asl)

        return VectorMatch(
            asl_gloss=adapted,
            source_english=entry["english"],
            source_pattern=pattern,
            cosine_similarity=best_dist,
        )


def _adapt_slots(query: str, pattern_english: str, asl_template: str) -> str:
    """
    Try to apply pattern_english's slots to the query to fill the ASL template.

    If adaptation fails, return asl_template as-is (slots replaced with a placeholder).
    """
    slot_names = re.findall(r"\{(\w+)\}", pattern_english)
    if not slot_names:
        # No slots — direct gloss
        return asl_template

    # Build pattern regex (same logic as PatternHashTable in Kotlin)
    regex_str = re.escape(pattern_english)
    for slot in slot_names:
        regex_str = regex_str.replace(rf"\{{{slot}\}}", rf"(?P<{slot}>.+?)")
    regex_str = rf"^{regex_str}[.?!]?$"

    m = re.match(regex_str, query, re.IGNORECASE)
    if not m:
        # Regex didn't match — strip slot placeholders from template
        result = asl_template
        for slot in slot_names:
            result = result.replace(f"{{{slot}}}", "")
        return " ".join(result.split())

    # Fill ASL template with extracted values
    result = asl_template
    for slot in slot_names:
        value = m.group(slot).upper()
        result = result.replace(f"{{{slot}}}", value)

    return result
