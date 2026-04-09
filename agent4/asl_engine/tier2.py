from __future__ import annotations

import math
import re
from typing import Protocol

from .normalize import normalize, fill_asl_template, build_slot_regex, SLOT_RE
from .types import TranslationOutput


class Embedder(Protocol):
    """Interface for sentence embedding. Production: MiniLM-L6 via ONNX."""

    def embed(self, text: str) -> list[float]: ...

    @property
    def dims(self) -> int: ...


class VectorEntry:
    __slots__ = ("embedding", "pattern", "asl_template", "slot_names")

    def __init__(
        self,
        embedding: list[float],
        pattern: str,
        asl_template: str,
        slot_names: list[str],
    ):
        self.embedding = embedding
        self.pattern = pattern
        self.asl_template = asl_template
        self.slot_names = slot_names


class Tier2:
    """Vector similarity search over embedded patterns."""

    def __init__(self, embedder: Embedder, threshold: float = 0.75):
        self.embedder = embedder
        self.threshold = threshold
        self.entries: list[VectorEntry] = []

    def add_pattern(
        self, pattern: str, asl_template: str, slot_names: list[str]
    ) -> None:
        emb = self.embedder.embed(pattern)
        self.entries.append(VectorEntry(emb, pattern, asl_template, slot_names))

    def translate(self, sentence: str) -> tuple[TranslationOutput | None, bool]:
        if not self.entries:
            return None, False

        emb = self.embedder.embed(sentence)

        best_idx = -1
        best_sim = -1.0
        for i, e in enumerate(self.entries):
            sim = _cosine_similarity(emb, e.embedding)
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        if best_idx < 0 or best_sim < self.threshold:
            return None, False

        best = self.entries[best_idx]
        gloss = _adapt_template(
            best.asl_template, best.pattern, best.slot_names, sentence
        )
        return TranslationOutput(
            asl_gloss=gloss,
            method="vector_similarity",
            pattern=best.pattern,
            confidence=best_sim,
        ), True


def _adapt_template(
    asl_template: str,
    matched_pattern: str,
    slot_names: list[str],
    input_sentence: str,
) -> list[str]:
    """Fill ASL template with slot values extracted from the input."""
    if not slot_names:
        return asl_template.upper().split()

    regex, _ = build_slot_regex(matched_pattern)
    if regex is not None:
        norm = normalize(input_sentence)
        m = regex.match(norm)
        if m is not None:
            slots = {k: v.upper() for k, v in m.groupdict().items()}
            return fill_asl_template(asl_template, slots)

    # Regex didn't match (approximate hit) — return template without slot markers
    cleaned = SLOT_RE.sub("", asl_template)
    return [t.strip("-").upper() for t in cleaned.split() if t.strip("-")]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# --- Bag-of-words embedder (dev/testing fallback) ---


class BagOfWordsEmbedder:
    """Hash-based BoW embedder for testing. Use MiniLM-L6 ONNX in production."""

    def __init__(self, dims: int = 384):
        self._dims = dims

    @property
    def dims(self) -> int:
        return self._dims

    def embed(self, text: str) -> list[float]:
        words = text.lower().split()
        vec = [0.0] * self._dims
        for w in words:
            idx = _fnv32a(w) % self._dims
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def _fnv32a(s: str) -> int:
    h = 2166136261
    for b in s.encode():
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return h
