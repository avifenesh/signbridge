"""
Tier 2: Build the FAISS index from the pattern corpus.

The index maps embedded English example sentences to ASL glosses.
At query time, we embed the input sentence and find the nearest neighbour.

Index format (flat cosine — since embeddings are L2-normalized, dot product ≈ cosine):
  faiss.IndexFlatIP (inner product = cosine on unit vectors)

Two output files:
  faiss.index    — binary FAISS index
  index_map.json — list of {"english", "asl", "pattern"} in insertion order
                   index_map[i] corresponds to vector i in faiss.index

Usage:
    python -m translation.tier2.build_index
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from translation.config import (
    ARTIFACTS_DIR,
    FAISS_INDEX,
    INDEX_MAP_JSON,
    MODEL_CACHE,
    ensure_dirs,
)
from translation.tier1.patterns import get_all_patterns_for_index
from translation.tier2.embed import MiniLMEmbedder


def build(
    index_path: Path = FAISS_INDEX,
    map_path: Path = INDEX_MAP_JSON,
    *,
    verbose: bool = True,
) -> tuple[Path, Path]:
    """Build and save the FAISS index + map. Return (index_path, map_path)."""
    try:
        import faiss
    except ImportError as e:
        raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu") from e

    ensure_dirs()

    # Collect corpus from Tier 1 augmented examples
    corpus = get_all_patterns_for_index()   # [(english, asl, pattern_english), ...]
    sentences = [item[0] for item in corpus]
    asl_glosses = [item[1] for item in corpus]
    patterns = [item[2] for item in corpus]

    if verbose:
        print(f"[tier2] Building index from {len(sentences)} examples…")

    # Embed all sentences
    embedder = MiniLMEmbedder(model_cache=MODEL_CACHE)
    embedder.load()
    vectors: np.ndarray = embedder.embed(sentences)   # (N, 384) float32, L2-normalized

    # Build flat inner-product index (cosine similarity on normalized vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    if verbose:
        print(f"[tier2] Index built: {index.ntotal} vectors, dim={dim}")

    # Save FAISS index
    faiss.write_index(index, str(index_path))

    # Save mapping: vector index → (english, asl_gloss, source_pattern)
    mapping = [
        {"english": eng, "asl": asl, "pattern": pat}
        for eng, asl, pat in zip(sentences, asl_glosses, patterns)
    ]
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    if verbose:
        size_index = index_path.stat().st_size / 1e6
        size_map = map_path.stat().st_size / 1024
        print(f"[tier2] Saved FAISS index ({size_index:.2f} MB) → {index_path}")
        print(f"[tier2] Saved index map ({size_map:.1f} KB) → {map_path}")

    return index_path, map_path


if __name__ == "__main__":
    build()
    sys.exit(0)
