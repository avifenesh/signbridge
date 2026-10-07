"""
Tier 3: Export trained T5-small checkpoint to ONNX INT8 for Android.

Target:
  - ONNX with INT8 dynamic quantization
  - Size: < 20MB (T5-small INT8 ≈ 60MB → needs aggressive quantization or ByT5-small)
  - Android loads via OnnxRuntime + NNAPI delegate for < 200ms inference

Two ONNX files are needed for T5 (encoder-decoder architecture):
  t5_encoder.onnx  — encodes the English input
  t5_decoder.onnx  — autoregressive decoding to generate ASL gloss tokens

Both are exported directly with torch.onnx (the input/output names match the
previous Optimum layout: encoder_model.onnx / decoder_model.onnx).

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
from translation._tokenizer_security import _install_chat_template_save_guard


def export_onnx(
    checkpoint_dir: Path,
    output_dir: Path = ARTIFACTS_DIR,
    *,
    quantize: bool = True,
    verbose: bool = True,
    opset: int = 17,
) -> tuple[Path, Path]:
    """
    Export T5 checkpoint to ONNX (encoder + decoder).
    Returns (encoder_path, decoder_path).

    encoder_model.onnx
      inputs : input_ids int64 [batch, src_seq], attention_mask int64 [batch, src_seq]
      output : last_hidden_state float32 [batch, src_seq, d_model]
    decoder_model.onnx (no KV cache; feed the full decoder prefix each step)
      inputs : input_ids int64 [batch, tgt_seq], encoder_attention_mask int64 [batch, src_seq],
               encoder_hidden_states float32 [batch, src_seq, d_model]
      output : logits float32 [batch, tgt_seq, vocab]
    """
    _install_chat_template_save_guard()
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as e:
        raise ImportError(
            "torch and transformers are required. Run: pip install -r translation/requirements.txt"
        ) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[tier3] Exporting {checkpoint_dir} → ONNX…")

    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(checkpoint_dir)).eval()
    tokenizer.save_pretrained(str(output_dir))

    encoder_path = output_dir / "encoder_model.onnx"
    decoder_path = output_dir / "decoder_model.onnx"
    _export_seq2seq(torch, model, encoder_path, decoder_path, opset=opset)

    if verbose:
        for p in [encoder_path, decoder_path]:
            if p.exists():
                print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")

    if quantize:
        encoder_q, decoder_q = _quantize_pair(encoder_path, decoder_path, verbose=verbose)
        return encoder_q, decoder_q

    return encoder_path, decoder_path


def _export_seq2seq(torch, model, encoder_path: Path, decoder_path: Path, *, opset: int) -> None:
    """Export the encoder and a cache-free decoder of a seq2seq model with torch.onnx."""

    class Encoder(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.encoder = model.get_encoder()

        def forward(self, input_ids, attention_mask):
            return self.encoder(
                input_ids=input_ids, attention_mask=attention_mask, return_dict=False
            )[0]

    class Decoder(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, input_ids, encoder_attention_mask, encoder_hidden_states):
            return self.model(
                attention_mask=encoder_attention_mask,
                decoder_input_ids=input_ids,
                encoder_outputs=(encoder_hidden_states,),
                use_cache=False,
                return_dict=False,
            )[0]

    src = torch.ones((1, 8), dtype=torch.long)
    # Trace with a padded mask so the exported graph keeps the masking path.
    src_mask = src.clone()
    src_mask[:, -2:] = 0
    tgt = torch.full((1, 4), model.config.decoder_start_token_id, dtype=torch.long)
    with torch.no_grad():
        hidden = Encoder(model)(src, src_mask)
        torch.onnx.export(
            Encoder(model),
            (src, src_mask),
            str(encoder_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "src_seq"},
                "attention_mask": {0: "batch", 1: "src_seq"},
                "last_hidden_state": {0: "batch", 1: "src_seq"},
            },
            opset_version=opset,
            dynamo=False,
        )
        torch.onnx.export(
            Decoder(model),
            (tgt, src_mask, hidden),
            str(decoder_path),
            input_names=["input_ids", "encoder_attention_mask", "encoder_hidden_states"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "tgt_seq"},
                "encoder_attention_mask": {0: "batch", 1: "src_seq"},
                "encoder_hidden_states": {0: "batch", 1: "src_seq"},
                "logits": {0: "batch", 1: "tgt_seq"},
            },
            opset_version=opset,
            dynamo=False,
        )


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
