"""Tier 2: FAISS vector similarity search.

Builds and queries a FAISS index of known English→ASL gloss pairs.
When a new sentence doesn't match tier 1 exactly, find the closest
known sentence and adapt its gloss.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from translation.config import (
    EMBEDDING_DIM,
    FAISS_INDEX,
    FAISS_TOP_K,
    INDEX_MAP_JSON,
    VECTOR_CONFIDENCE_THRESHOLD,
)
from translation.types import TranslationMethod, TranslationResult


@dataclass
class IndexEntry:
    """A single entry in the FAISS index metadata."""

    english: str
    asl_gloss: list[str]


class SimilaritySearch:
    """Tier 2 translation: vector similarity via FAISS."""

    def __init__(self):
        self._index = None
        self._entries: list[IndexEntry] = []
        self._loaded = False

    def build_index(
        self,
        pairs: list[tuple[str, list[str]]],
        output_dir: Path | None = None,
    ) -> None:
        """Build a FAISS index from English→gloss pairs.

        Args:
            pairs: List of (english_sentence, asl_gloss_list) tuples.
            output_dir: Where to save the index files.
        """
        import faiss

        from translation.tier2.embeddings import SentenceEmbedder

        if not pairs:
            raise ValueError("No pairs to index")

        embedder = SentenceEmbedder()
        sentences = [p[0] for p in pairs]
        embeddings = embedder.embed(sentences)

        # Build FAISS index (inner product on normalized vectors = cosine similarity)
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        index.add(embeddings)

        # Save
        out = output_dir or FAISS_INDEX.parent
        out.mkdir(parents=True, exist_ok=True)

        index_path = out / FAISS_INDEX.name
        map_path = out / INDEX_MAP_JSON.name

        faiss.write_index(index, str(index_path))

        metadata = [{"english": p[0], "asl_gloss": p[1]} for p in pairs]
        with open(map_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self._index = index
        self._entries = [IndexEntry(english=p[0], asl_gloss=p[1]) for p in pairs]
        self._loaded = True

        return index_path, map_path

    def load(self, index_dir: Path | None = None) -> None:
        """Load a pre-built FAISS index."""
        import faiss

        base = index_dir or FAISS_INDEX.parent
        index_path = base / FAISS_INDEX.name if index_dir else FAISS_INDEX
        map_path = base / INDEX_MAP_JSON.name if index_dir else INDEX_MAP_JSON

        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not map_path.exists():
            raise FileNotFoundError(f"Index metadata not found: {map_path}")

        self._index = faiss.read_index(str(index_path))

        with open(map_path) as f:
            metadata = json.load(f)
        self._entries = [IndexEntry(**m) for m in metadata]
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def search(self, sentence: str, top_k: int = FAISS_TOP_K) -> list[tuple[IndexEntry, float]]:
        """Find the top-K most similar sentences.

        Returns:
            List of (IndexEntry, cosine_similarity) tuples, sorted by similarity desc.
        """
        self._ensure_loaded()

        from translation.tier2.embeddings import SentenceEmbedder

        embedder = SentenceEmbedder()
        query = embedder.embed_one(sentence).reshape(1, -1)

        scores, indices = self._index.search(query, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._entries):
                results.append((self._entries[idx], float(score)))
        return results

    def translate(self, sentence: str) -> TranslationResult | None:
        """Try tier 2: find closest known sentence and return its gloss.

        Only returns a result if similarity >= VECTOR_CONFIDENCE_THRESHOLD.
        """
        try:
            candidates = self.search(sentence)
        except (FileNotFoundError, RuntimeError):
            return None

        if not candidates:
            return None

        best_entry, best_score = candidates[0]
        if best_score < VECTOR_CONFIDENCE_THRESHOLD:
            return None

        return TranslationResult(
            asl_gloss=list(best_entry.asl_gloss),
            method=TranslationMethod.SIMILARITY,
            confidence=round(best_score, 3),
            english=sentence,
            debug={
                "matched": best_entry.english,
                "score": round(best_score, 3),
                "candidates": [
                    {"english": e.english, "score": round(s, 3)}
                    for e, s in candidates
                ],
            },
        )

    @property
    def index_size(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal
