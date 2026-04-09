"""
Tier 3: Export trained T5-small checkpoint to ONNX INT8 for Android.

Target:
  - ONNX with INT8 dynamic quantization
  - Size: < 20MB (T5-small INT8 ≈ 60MB → needs aggressive quantization or ByT5-small)
  - Android loads via OnnxRuntime + NNAPI delegate for < 200ms inference

Two ONNX files are needed for T5 (encoder-decoder architecture):
  t5_encoder.onnx  — encodes the English input
  t5_decoder.onnx  — autoregressive decoding to generate ASL gloss tokens

Or use optimum's export which handles this automatically.

Usage:
    python -m translation.tier3.export_onnx \
        --checkpoint .translation_cache/checkpoints/best \
        --output app/src/main/assets/translation/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from translation.config import ARTIFACTS_DIR, CACHE_DIR, T5_ONNX


def export_onnx(
    checkpoint_dir: Path,
    output_dir: Path = ARTIFACTS_DIR,
    *,
    quantize: bool = True,
    verbose: bool = True,
) -> tuple[Path, Path]:
    """
    Export T5 checkpoint to ONNX (encoder + decoder).
    Returns (encoder_path, decoder_path).
    """
    try:
        from optimum.onnxruntime import ORTModelForSeq2SeqLM
        from transformers import AutoTokenizer
    except ImportError as e:
        raise ImportError(
            "optimum[onnxruntime] not installed. Run: pip install optimum[onnxruntime]"
        ) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[tier3] Exporting {checkpoint_dir} → ONNX…")

    # Export via Optimum (handles encoder/decoder split automatically)
    ort_model = ORTModelForSeq2SeqLM.from_pretrained(
        str(checkpoint_dir),
        export=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))

    ort_model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    encoder_path = output_dir / "encoder_model.onnx"
    decoder_path = output_dir / "decoder_model.onnx"

    if verbose:
        for p in [encoder_path, decoder_path]:
            if p.exists():
                print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")

    if quantize:
        encoder_q, decoder_q = _quantize_pair(encoder_path, decoder_path, verbose=verbose)
        return encoder_q, decoder_q

    return encoder_path, decoder_path


def _quantize_pair(
    encoder_path: Path, decoder_path: Path, *, verbose: bool = True
) -> tuple[Path, Path]:
    """Apply INT8 dynamic quantization to encoder and decoder ONNX models."""
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError as e:
        raise ImportError("onnxruntime not installed") from e

    pairs = [
        (encoder_path, encoder_path.with_stem(encoder_path.stem + "_int8")),
        (decoder_path, decoder_path.with_stem(decoder_path.stem + "_int8")),
    ]
    results = []
    for src, dst in pairs:
        if not src.exists():
            if verbose:
                print(f"  [skip] {src.name} not found")
            continue
        quantize_dynamic(str(src), str(dst), weight_type=QuantType.QInt8)
        if verbose:
            before = src.stat().st_size / 1e6
            after = dst.stat().st_size / 1e6
            print(f"  Quantized {src.name}: {before:.1f}MB → {after:.1f}MB")
        results.append(dst)

    if len(results) == 2:
        return results[0], results[1]
    raise RuntimeError(f"Quantization failed — found {len(results)}/2 output files")


def check_size_budget(encoder_path: Path, decoder_path: Path) -> bool:
    """Verify the combined ONNX size fits the 20MB budget."""
    total_mb = sum(
        p.stat().st_size / 1e6
        for p in [encoder_path, decoder_path]
        if p.exists()
    )
    budget_mb = 20.0
    ok = total_mb <= budget_mb
    status = "✓" if ok else "✗ OVER BUDGET"
    print(f"[tier3] Total ONNX size: {total_mb:.1f}MB / {budget_mb:.0f}MB {status}")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export T5 checkpoint to ONNX INT8")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument("--no-quantize", action="store_true")
    args = parser.parse_args()

    enc, dec = export_onnx(args.checkpoint, args.output, quantize=not args.no_quantize)
    ok = check_size_budget(enc, dec)
    sys.exit(0 if ok else 1)
