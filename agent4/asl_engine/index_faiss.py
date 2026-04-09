"""Optional FAISS index for fast vector similarity search.

Falls back gracefully if faiss-cpu is not installed.
Use for 1000+ patterns where flat cosine scan becomes slow.

Install: pip install faiss-cpu numpy
"""
from __future__ import annotations

from pathlib import Path

try:
    import faiss
    import numpy as np

    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False


def faiss_available() -> bool:
    return _HAS_FAISS


class FaissIndex:
    """Wrapper around FAISS for nearest-neighbor search on L2-normalized vectors.

    Uses IndexFlatIP (inner product = cosine similarity on normalized vectors)
    by default. Switch to IndexIVFPQ for 10K+ patterns.
    """

    def __init__(self, dims: int):
        if not _HAS_FAISS:
            raise RuntimeError("faiss-cpu required: pip install faiss-cpu")
        self._dims = dims
        self._index = faiss.IndexFlatIP(dims)
        self._meta: list[dict] = []

    def add(
        self,
        embedding: list[float],
        pattern: str,
        asl_template: str,
        slot_names: list[str],
    ) -> None:
        vec = np.array([embedding], dtype=np.float32)
        self._index.add(vec)
        self._meta.append({
            "pattern": pattern,
            "asl_template": asl_template,
            "slot_names": slot_names,
        })

    def search(
        self, embedding: list[float], k: int = 3
    ) -> list[tuple[float, dict]]:
        """Return top-k matches as (score, metadata) tuples."""
        vec = np.array([embedding], dtype=np.float32)
        scores, indices = self._index.search(vec, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((float(score), self._meta[idx]))
        return results

    @property
    def size(self) -> int:
        return self._index.ntotal

    def save(self, path: str | Path) -> None:
        """Save FAISS index to disk (metadata saved alongside as .meta.json)."""
        import json

        faiss.write_index(self._index, str(path))
        meta_path = Path(str(path) + ".meta.json")
        meta_path.write_text(json.dumps(self._meta))

    @classmethod
    def load(cls, path: str | Path, dims: int) -> FaissIndex:
        """Load a saved FAISS index from disk."""
        import json

        obj = cls.__new__(cls)
        obj._dims = dims
        obj._index = faiss.read_index(str(path))
        meta_path = Path(str(path) + ".meta.json")
        obj._meta = json.loads(meta_path.read_text())
        return obj
