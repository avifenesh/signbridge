from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .types import (
    STTOutput,
    TranslationOutput,
    SignEntry,
    SignSequence,
    SignType,
    LowConfidenceError,
)
from .tier1 import Tier1
from .tier2 import Tier2, BagOfWordsEmbedder, Embedder
from .tier3 import Tier3
from .dictionary import SignDictionary
from .fingerspell import fingerspell


@dataclass
class Config:
    patterns_path: str | Path
    dictionary_path: str | Path | None = None
    models_dir: str | Path | None = None  # path to MiniLM ONNX model dir
    embedder: Embedder | None = None
    tier2_threshold: float = 0.75
    min_stt_confidence: float = 0.3


class Engine:
    """3-tier ASL translation engine."""

    def __init__(self, cfg: Config):
        self._tier1 = Tier1(cfg.patterns_path)

        embedder = cfg.embedder
        if embedder is None and cfg.models_dir is not None:
            from .embedder_minilm import try_load_minilm
            embedder = try_load_minilm(cfg.models_dir)
        if embedder is None:
            embedder = BagOfWordsEmbedder(384)
        self._tier2 = Tier2(embedder, cfg.tier2_threshold)

        # Index all tier1 patterns into tier2 for similarity fallback
        for p in self._tier1.patterns:
            self._tier2.add_pattern(p.pattern, p.asl_template, p.slot_names)

        self._tier3 = Tier3()
        self._dict = SignDictionary(cfg.dictionary_path)
        self._min_stt_confidence = cfg.min_stt_confidence

    def translate(self, stt: STTOutput) -> SignSequence:
        """Run the 3-tier pipeline. Raises LowConfidenceError for garbage STT."""
        # Gate: reject low-confidence STT (don't sign garbage)
        if stt.confidence > 0 and stt.confidence < self._min_stt_confidence:
            raise LowConfidenceError(stt.sentence, stt.confidence, self._min_stt_confidence)

        # Tier 1: pattern hash table
        out, ok = self._tier1.translate(stt.sentence)
        if ok and out is not None:
            return self._build_sequence(stt, out)

        # Tier 2: vector similarity
        out, ok = self._tier2.translate(stt.sentence)
        if ok and out is not None:
            return self._build_sequence(stt, out)

        # Tier 3: fine-tuned model (stub in V1)
        out, ok = self._tier3.translate(stt.sentence)
        if ok and out is not None:
            return self._build_sequence(stt, out)

        # Fallback: word-by-word (not proper ASL grammar, but no word is skipped)
        return self._fallback_translate(stt)

    def _build_sequence(self, stt: STTOutput, trans: TranslationOutput) -> SignSequence:
        stt_conf = stt.confidence if stt.confidence > 0 else 1.0
        return SignSequence(
            type="sign_sequence",
            english=stt.sentence,
            pipeline_confidence=stt_conf * trans.confidence,
            gloss=trans.asl_gloss,
            signs=[self._lookup_sign(g) for g in trans.asl_gloss],
        )

    def _fallback_translate(self, stt: STTOutput) -> SignSequence:
        words = stt.sentence.split()
        gloss = [w.upper() for w in words]
        stt_conf = stt.confidence if stt.confidence > 0 else 1.0
        return SignSequence(
            type="sign_sequence",
            english=stt.sentence,
            pipeline_confidence=stt_conf * 0.3,
            gloss=gloss,
            signs=[self._lookup_sign(g) for g in gloss],
        )

    def _lookup_sign(self, gloss: str) -> SignEntry:
        # Exact match
        entry = self._dict.lookup(gloss)
        if entry is not None:
            return entry

        # Compound gloss (e.g. GIVE-YOU): try base form
        if "-" in gloss:
            base = gloss.split("-", 1)[0]
            entry = self._dict.lookup(base)
            if entry is not None:
                entry.gloss = gloss  # preserve full gloss
                return entry

        return fingerspell(gloss)
