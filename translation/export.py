"""
One-shot artifact export for Android.

Builds all translation artifacts and places them in:
  app/src/main/assets/translation/

Artifacts produced:
  patterns.json    — Tier 1 pattern hash table
  faiss.index      — Tier 2 FAISS vector index  (requires sentence-transformers)
  index_map.json   — Tier 2 vector → ASL mapping (requires sentence-transformers)
  minilm.onnx      — Tier 2 MiniLM ONNX model   (requires optimum)
  t5_encoder_int8.onnx / t5_decoder_int8.onnx   (requires checkpoint from training)

Usage:
    python -m translation.export                  # Tier 1 + Tier 2 (if deps installed)
    python -m translation.export --all            # Include Tier 3 ONNX export
    python -m translation.export --tier1-only     # Pattern table only (no deps needed)
    python -m translation.export --t3-checkpoint path/to/checkpoint
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from translation.config import (
    ARTIFACTS_DIR,
    FAISS_INDEX,
    INDEX_MAP_JSON,
    MINILM_ONNX,
    MODEL_CACHE,
    PATTERNS_JSON,
    T5_ONNX,
    ensure_dirs,
)


def export_tier1(verbose: bool = True) -> bool:
    from translation.tier1.export_json import export, _verify_round_trip
    try:
        out = export(PATTERNS_JSON, verbose=verbose)
        return _verify_round_trip(out)
    except Exception as e:
        print(f"[export] Tier 1 failed: {e}")
        return False


def export_tier2_index(verbose: bool = True) -> bool:
    try:
        from translation.tier2.build_index import build
        build(FAISS_INDEX, INDEX_MAP_JSON, verbose=verbose)
        return True
    except ImportError as e:
        print(f"[export] Tier 2 index skipped (missing deps): {e}")
        return False
    except Exception as e:
        print(f"[export] Tier 2 index failed: {e}")
        return False


def export_tier2_onnx(verbose: bool = True) -> bool:
    try:
        from translation.tier2.embed import MiniLMEmbedder
        embedder = MiniLMEmbedder(model_cache=MODEL_CACHE)
        embedder.load()
        embedder.export_onnx(MINILM_ONNX)
        return True
    except ImportError as e:
        print(f"[export] MiniLM ONNX skipped (missing deps): {e}")
        return False
    except Exception as e:
        print(f"[export] MiniLM ONNX export failed: {e}")
        return False


def export_tier3_onnx(checkpoint: Path, verbose: bool = True) -> bool:
    try:
        from translation.tier3.export_onnx import export_onnx, check_size_budget
        enc, dec = export_onnx(checkpoint, ARTIFACTS_DIR, verbose=verbose)
        return check_size_budget(enc, dec)
    except ImportError as e:
        print(f"[export] Tier 3 ONNX skipped (missing deps): {e}")
        return False
    except Exception as e:
        print(f"[export] Tier 3 ONNX export failed: {e}")
        return False


def print_summary() -> None:
    print("\n── Artifact Summary ─────────────────────────────────")
    artifacts = [
        ("Tier 1 patterns", PATTERNS_JSON),
        ("Tier 2 FAISS index", FAISS_INDEX),
        ("Tier 2 index map", INDEX_MAP_JSON),
        ("Tier 2 MiniLM ONNX", MINILM_ONNX),
    ]
    for name, path in artifacts:
        if path.exists():
            size = path.stat().st_size
            size_str = f"{size / 1e6:.2f} MB" if size > 1e5 else f"{size / 1e3:.1f} KB"
            print(f"  ✓ {name:25s} {size_str}")
        else:
            print(f"  ✗ {name:25s} (not built)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build all SignBridge translation artifacts for Android"
    )
    parser.add_argument("--tier1-only", action="store_true",
                        help="Export Tier 1 pattern JSON only (no ML deps required)")
    parser.add_argument("--all", action="store_true",
                        help="Include Tier 3 ONNX export (requires trained checkpoint)")
    parser.add_argument("--t3-checkpoint", type=Path,
                        help="Path to T5 checkpoint for Tier 3 export")
    parser.add_argument("--skip-onnx", action="store_true",
                        help="Skip ONNX export (faster, index only)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    verbose = not args.quiet
    ensure_dirs()

    results = {}

    # Tier 1 — always
    print("[export] Building Tier 1 (pattern table)…")
    results["tier1"] = export_tier1(verbose=verbose)

    if args.tier1_only:
        print_summary()
        return 0 if all(results.values()) else 1

    # Tier 2 — requires ML deps
    print("[export] Building Tier 2 (FAISS index)…")
    results["tier2_index"] = export_tier2_index(verbose=verbose)

    if not args.skip_onnx:
        print("[export] Exporting Tier 2 MiniLM ONNX…")
        results["tier2_onnx"] = export_tier2_onnx(verbose=verbose)

    # Tier 3 — only if checkpoint provided
    if args.t3_checkpoint or args.all:
        checkpoint = args.t3_checkpoint
        if checkpoint and checkpoint.exists():
            print("[export] Exporting Tier 3 T5 ONNX…")
            results["tier3_onnx"] = export_tier3_onnx(checkpoint, verbose=verbose)
        else:
            print("[export] Tier 3 skipped — no checkpoint (train first with translation/tier3/train.py)")

    print_summary()

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n[export] Failed: {failed}")
        return 1

    print("\n[export] All artifacts built successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
