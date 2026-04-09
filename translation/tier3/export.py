"""Export trained T5 model to ONNX format for Android deployment.

V1 status: PLACEHOLDER — requires training data and fine-tuned model.
This module will convert a Hugging Face T5 checkpoint to ONNX.
"""

from __future__ import annotations

from pathlib import Path

from translation.config import CHECKPOINTS_DIR, T5_ONNX


def export_to_onnx(
    checkpoint_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Export a fine-tuned T5 model to ONNX.

    Args:
        checkpoint_dir: Directory containing the trained model.
        output_path: Where to write the ONNX file.

    Returns:
        Path to the exported ONNX model.

    Raises:
        NotImplementedError: Always in V1 — requires training pipeline.
    """
    raise NotImplementedError(
        "Tier 3 ONNX export requires a trained model. "
        "Training pipeline not yet implemented — V1 ships with tiers 1+2. "
        "See SPEC.md: 'If insufficient data: ship V1 with tiers 1+2 only, "
        "tier 3 marked experimental.'"
    )
