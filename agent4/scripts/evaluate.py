#!/usr/bin/env python3
"""Evaluate the ASL translation engine against test fixtures.

Measures: tier hit rates, accuracy, confidence distribution, fallback rate.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asl_engine.engine import Engine, Config
from asl_engine.types import STTOutput, LowConfidenceError

DATA = ROOT / "data"


def main() -> None:
    eval_path = DATA / "eval_set.json"
    if not eval_path.exists():
        print(f"No eval set at {eval_path}")
        sys.exit(1)

    fixtures = json.loads(eval_path.read_text())
    print(f"Loaded {len(fixtures)} evaluation cases")

    eng = Engine(Config(
        patterns_path=DATA / "patterns.json",
        dictionary_path=DATA / "dictionary.json",
    ))

    tier_counts: dict[str, int] = {}
    correct = 0
    total = 0
    confidences: list[float] = []
    fallback_count = 0
    latencies: list[float] = []

    for case in fixtures:
        sentence = case["sentence"]
        expected = case.get("expected_gloss")

        stt = STTOutput(sentence=sentence, confidence=0.95, source="eval")

        t0 = time.perf_counter()
        try:
            seq = eng.translate(stt)
        except LowConfidenceError:
            continue
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

        # Determine which tier produced the result
        # Check pipeline confidence: 0.95 * 1.0 = tier1, 0.95 * <1.0 = tier2, 0.95 * 0.3 = fallback
        pc = seq.pipeline_confidence
        if pc >= 0.94:
            tier = "tier1"
        elif pc >= 0.5:
            tier = "tier2"
        elif pc > 0.3:
            tier = "tier3_or_fallback"
        else:
            tier = "fallback"
            fallback_count += 1

        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        confidences.append(seq.pipeline_confidence)
        total += 1

        if expected is not None:
            if seq.gloss == expected:
                correct += 1

    # Report
    print("\n=== Evaluation Report ===\n")
    print(f"Total cases:     {total}")
    print(f"Tier distribution:")
    for tier, count in sorted(tier_counts.items()):
        pct = count / total * 100 if total else 0
        print(f"  {tier:20s}: {count:4d} ({pct:.1f}%)")

    if any(c.get("expected_gloss") for c in fixtures):
        cases_with_expected = sum(1 for c in fixtures if c.get("expected_gloss"))
        print(f"\nAccuracy (where expected_gloss provided):")
        print(f"  {correct}/{cases_with_expected} = {correct/max(cases_with_expected,1)*100:.1f}%")

    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        print(f"\nConfidence: avg={avg_conf:.3f}  min={min_conf:.3f}  max={max_conf:.3f}")

    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"Latency:   avg={avg_lat:.2f}ms  p95={p95:.2f}ms  max={max_lat:.2f}ms")

    print(f"\nFallback rate: {fallback_count}/{total} ({fallback_count/max(total,1)*100:.1f}%)")


if __name__ == "__main__":
    main()
