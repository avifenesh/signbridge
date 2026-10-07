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

Template-aware reranking:
  Corpus vectors are slot-filled examples ("i like pizza", "i want coffee").
  MiniLM weights the slot filler heavily, so a query can land closer to an
  example of the wrong template that happens to share its filler ("i want
  pizza" -> "i like pizza") than to the right template with a different
  filler. Before taking the raw nearest neighbour we therefore check the
  top-k candidates for one whose source pattern fully matches the query.
  Such a candidate is scored against its pattern re-filled with the query's
  own slot values, so the filler difference with the stored example no
  longer counts as semantic distance.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
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

    def query(self, sentence: str, top_k: int = 10) -> VectorMatch | None:
        """
        Find nearest ASL match for an English sentence.

        Returns None if best cosine similarity is below threshold.
        Applies slot adaptation when the matched pattern has {SLOT} placeholders.
        Among the top_k candidates, one whose source pattern fully matches the
        query wins over the raw nearest neighbour (see module docstring).
        """
        if not self._loaded:
            raise RuntimeError("Call load() before query()")

        query = sentence.lower()
        vec = self._embedder.embed_one(query)
        distances, indices = self._index.search(vec.reshape(1, -1), top_k)

        best_idx, best_sim = self._template_match(query, vec, distances[0], indices[0])
        if best_idx is None:
            best_idx, best_sim = int(indices[0][0]), float(distances[0][0])

        if best_idx < 0 or best_sim < self.threshold:
            return None

        entry = self._mapping[best_idx]
        asl = entry["asl"]
        pattern = entry["pattern"]

        # Attempt slot adaptation if the source pattern has slots
        adapted = _adapt_slots(query, pattern, asl)

        return VectorMatch(
            asl_gloss=adapted,
            source_english=entry["english"],
            source_pattern=pattern,
            cosine_similarity=best_sim,
        )

    def _template_match(
        self,
        query: str,
        query_vec: np.ndarray,
        distances: np.ndarray,
        indices: np.ndarray,
    ) -> tuple[int | None, float]:
        """Return (index, similarity) of the first candidate, in cosine order,
        whose source pattern fully matches the query, or (None, 0.0) if none does.

        Its similarity is the cosine between the query and the pattern filled
        with the query's own slot values.
        """
        for idx in indices:
            idx = int(idx)
            if idx < 0:
                continue
            pattern = self._mapping[idx]["pattern"]
            m = _pattern_regex(pattern).match(query)
            if not m:
                continue
            filled = pattern
            for slot, value in m.groupdict().items():
                filled = filled.replace(f"{{{slot}}}", value)
            filled_vec = self._embedder.embed_one(filled)
            return idx, float(np.dot(query_vec, filled_vec))
        return None, 0.0


@lru_cache(maxsize=None)
def _pattern_regex(pattern_english: str) -> re.Pattern[str]:
    """Compile a pattern like "i want {THING}" into an anchored regex.

    Same logic as PatternHashTable in Kotlin: each {SLOT} becomes a lazy named
    group and an optional trailing [.?!] is allowed.
    """
    regex_str = re.escape(pattern_english)
    for slot in re.findall(r"\{(\w+)\}", pattern_english):
        regex_str = regex_str.replace(rf"\{{{slot}\}}", rf"(?P<{slot}>.+?)")
    return re.compile(rf"^{regex_str}[.?!]?$", re.IGNORECASE)


def _adapt_slots(query: str, pattern_english: str, asl_template: str) -> str:
    """
    Try to apply pattern_english's slots to the query to fill the ASL template.

    If adaptation fails, return asl_template as-is (slots replaced with a placeholder).
    """
    slot_names = re.findall(r"\{(\w+)\}", pattern_english)
    if not slot_names:
        # No slots — direct gloss
        return asl_template

    m = _pattern_regex(pattern_english).match(query)
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
