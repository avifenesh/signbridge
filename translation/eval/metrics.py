"""
Evaluation metrics for the ASL translation pipeline.

Metrics:
  - Tier 1 hit rate: % of sentences matched by pattern hash
  - Tier 2 hit rate: % of sentences matched by vector similarity (threshold >= 0.75)
  - Tier 3 hit rate: % reaching the model tier
  - BLEU score: for Tier 3 model output vs reference glosses
  - Token accuracy: exact-match on gloss token sequence
  - Per-category hit rates

Usage:
    from translation.eval.metrics import evaluate_pipeline
    results = evaluate_pipeline(test_pairs)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from translation.tier1.patterns import PATTERNS


@dataclass
class EvalResult:
    total: int = 0
    tier1_hits: int = 0
    tier2_hits: int = 0
    tier3_hits: int = 0
    fallback_hits: int = 0   # fingerspell / word-order fallback

    tier1_correct: int = 0   # hits that produced correct gloss
    tier2_correct: int = 0
    tier3_bleu: float = 0.0

    per_category: dict[str, dict] = field(default_factory=dict)

    @property
    def tier1_rate(self) -> float:
        return self.tier1_hits / self.total if self.total else 0.0

    @property
    def tier2_rate(self) -> float:
        return self.tier2_hits / self.total if self.total else 0.0

    @property
    def tier3_rate(self) -> float:
        return self.tier3_hits / self.total if self.total else 0.0

    @property
    def coverage(self) -> float:
        """Fraction of inputs handled by Tier 1 or 2 (high-confidence)."""
        return (self.tier1_hits + self.tier2_hits) / self.total if self.total else 0.0

    def print_summary(self) -> None:
        print("=" * 50)
        print(f"Total sentences: {self.total}")
        print(f"Tier 1 (pattern): {self.tier1_hits:4d} ({self.tier1_rate:.1%})")
        print(f"Tier 2 (vector):  {self.tier2_hits:4d} ({self.tier2_rate:.1%})")
        print(f"Tier 3 (model):   {self.tier3_hits:4d} ({self.tier3_rate:.1%})")
        print(f"Fallback:         {self.fallback_hits:4d}")
        print(f"Coverage (T1+T2): {self.coverage:.1%}")
        if self.tier3_bleu:
            print(f"Tier 3 BLEU:      {self.tier3_bleu:.3f}")
        print("=" * 50)


def evaluate_tier1_hit_rate(
    sentences: list[str],
    *,
    verbose: bool = False,
) -> EvalResult:
    """
    Evaluate Tier 1 hit rate on a list of sentences.
    Does not require FAISS or models — pure pattern matching.
    """
    import re

    result = EvalResult(total=len(sentences))

    # Build the same pattern table as PatternHashTable
    pattern_entries = []
    for p in PATTERNS:
        english = p["english"]
        slot_names = re.findall(r"\{(\w+)\}", english)
        regex_str = re.escape(english)
        for slot in slot_names:
            regex_str = regex_str.replace(rf"\{{{slot}\}}", rf"(?P<{slot}>.+?)")
        regex_str = rf"^{regex_str}[.?!]?$"
        pattern_entries.append((
            re.compile(regex_str, re.IGNORECASE),
            p["asl"],
            p["category"],
        ))

    for sentence in sentences:
        normalized = sentence.lower().strip()
        matched = False
        for regex, asl, category in pattern_entries:
            if regex.match(normalized):
                result.tier1_hits += 1
                cat = result.per_category.setdefault(category, {"hits": 0, "total": 0})
                cat["hits"] += 1
                matched = True
                if verbose:
                    print(f"  T1 hit: {sentence!r:50s} → {asl}")
                break

        cat = result.per_category.setdefault(
            next((p["category"] for p in PATTERNS), "other"), {"hits": 0, "total": 0}
        )
        result.per_category.setdefault("_total", {"hits": 0, "total": 0})["total"] += 1

    return result


def evaluate_pipeline(
    test_pairs: list[dict],
    *,
    faiss_index_path: Path | None = None,
    index_map_path: Path | None = None,
    tier3_checkpoint: Path | None = None,
) -> EvalResult:
    """
    Full pipeline evaluation.

    test_pairs: list of {"english": ..., "asl": ..., "source": ..., "confidence": ...}
    """
    from translation.config import FAISS_INDEX, INDEX_MAP_JSON, MODEL_CACHE

    result = EvalResult(total=len(test_pairs))

    # Build Tier 1 matcher
    import re
    pattern_entries = []
    for p in PATTERNS:
        english = p["english"]
        slot_names = re.findall(r"\{(\w+)\}", english)
        regex_str = re.escape(english)
        for slot in slot_names:
            regex_str = regex_str.replace(rf"\{{{slot}\}}", rf"(?P<{slot}>.+?)")
        regex_str = rf"^{regex_str}[.?!]?$"
        pattern_entries.append((
            re.compile(regex_str, re.IGNORECASE),
            p["asl"],
            p["category"],
        ))

    # Load Tier 2 if available
    tier2 = None
    idx_path = faiss_index_path or FAISS_INDEX
    map_path = index_map_path or INDEX_MAP_JSON
    if idx_path.exists():
        try:
            from translation.tier2.query import VectorIndex
            tier2 = VectorIndex(idx_path, map_path).load()
        except Exception as e:
            print(f"[eval] Tier 2 unavailable: {e}")

    tier3_sentences = []
    tier3_references = []

    for pair in test_pairs:
        english = pair["english"].lower().strip()
        reference_asl = pair["asl"]

        # Tier 1
        t1_hit = False
        for regex, asl, category in pattern_entries:
            if regex.match(english):
                result.tier1_hits += 1
                if _asl_match(asl, reference_asl):
                    result.tier1_correct += 1
                t1_hit = True
                break
        if t1_hit:
            continue

        # Tier 2
        if tier2 is not None:
            try:
                match = tier2.query(english)
                if match is not None:
                    result.tier2_hits += 1
                    if _asl_match(match.asl_gloss, reference_asl):
                        result.tier2_correct += 1
                    continue
            except Exception:
                pass

        # Reached Tier 3
        result.tier3_hits += 1
        tier3_sentences.append(english)
        tier3_references.append(reference_asl)

    # Score Tier 3 outputs if model available
    if tier3_checkpoint and tier3_sentences:
        try:
            from translation.tier3.train import generate
            predictions = generate(tier3_checkpoint, tier3_sentences)
            result.tier3_bleu = _compute_bleu(predictions, tier3_references)
        except Exception as e:
            print(f"[eval] Tier 3 scoring failed: {e}")

    result.fallback_hits = (
        result.total - result.tier1_hits - result.tier2_hits - result.tier3_hits
    )

    return result


def _asl_match(predicted: str, reference: str) -> bool:
    """Lenient ASL gloss match: normalize and compare token sets."""
    def normalize(s: str) -> set[str]:
        return set(s.upper().split())
    return normalize(predicted) == normalize(reference)


def _compute_bleu(predictions: list[str], references: list[str]) -> float:
    """Compute corpus BLEU score on gloss token sequences."""
    try:
        from sacrebleu.metrics import BLEU
        bleu = BLEU(effective_order=True)
        score = bleu.corpus_score(predictions, [references])
        return score.score / 100.0
    except ImportError:
        # Fallback: simple token-level accuracy
        correct = sum(
            1 for p, r in zip(predictions, references) if p.strip() == r.strip()
        )
        return correct / len(predictions) if predictions else 0.0


def evaluate_from_jsonl(
    jsonl_path: Path,
    *,
    sample_size: int | None = None,
    verbose: bool = True,
) -> EvalResult:
    """Load a JSONL file and run full evaluation."""
    with open(jsonl_path, encoding="utf-8") as f:
        pairs = [json.loads(line) for line in f if line.strip()]

    if sample_size:
        import random
        pairs = random.sample(pairs, min(sample_size, len(pairs)))

    if verbose:
        print(f"[eval] Evaluating {len(pairs)} pairs from {jsonl_path.name}…")

    result = evaluate_pipeline(pairs)

    if verbose:
        result.print_summary()

    return result
