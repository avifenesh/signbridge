"""Sentence embeddings for tier 2 vector similarity.

Uses sentence-transformers (all-MiniLM-L6-v2) to embed English sentences.
Heavy dependency — only imported when tier 2 is actually used.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from translation.config import EMBEDDING_DIM, MINILM_MODEL_NAME, MODEL_CACHE


class SentenceEmbedder:
    """Embed English sentences into dense vectors."""

    def __init__(self, model_name: str = MINILM_MODEL_NAME):
        self._model_name = model_name
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            cache_dir = str(MODEL_CACHE)
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            self._model = SentenceTransformer(self._model_name, cache_folder=cache_dir)

    def embed(self, sentences: list[str]) -> np.ndarray:
        """Embed a list of sentences.

        Args:
            sentences: List of English sentences.

        Returns:
            numpy array of shape (len(sentences), EMBEDDING_DIM).
        """
        self._ensure_loaded()
        embeddings = self._model.encode(
            sentences,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_one(self, sentence: str) -> np.ndarray:
        """Embed a single sentence. Returns shape (EMBEDDING_DIM,)."""
        return self.embed([sentence])[0]
