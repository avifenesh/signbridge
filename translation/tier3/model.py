"""Tier 3: Small seq2seq model for English → ASL gloss translation.

V1 status: EXPERIMENTAL — ships only if sufficient training data exists.
If data is insufficient, tiers 1+2 handle everything and tier 3 is a no-op.

Target: T5-small fine-tuned, exported to ONNX (<20MB), <200ms on Snapdragon 600.
"""

from __future__ import annotations

from pathlib import Path

from translation.config import T5_ONNX
from translation.types import TranslationMethod, TranslationResult


class GlossModel:
    """Tier 3 translation: seq2seq model (T5-small → ONNX).

    In V1 this is a stub that reports itself as unavailable unless
    a trained ONNX model exists at the expected path.
    """

    def __init__(self, model_path: Path | None = None):
        self._model_path = model_path or T5_ONNX
        self._session = None
        self._tokenizer = None
        self._available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if a trained model exists."""
        self._available = self._model_path.exists()

    @property
    def available(self) -> bool:
        return self._available

    def load(self) -> None:
        """Load the ONNX model for inference.

        Requires onnxruntime and the model file to exist.
        """
        if not self._available:
            raise RuntimeError(
                "Tier 3 model not available. Train and export first, "
                "or use tiers 1+2 only."
            )

        import onnxruntime as ort

        self._session = ort.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],
        )

    def translate(self, sentence: str) -> TranslationResult | None:
        """Try tier 3: model inference.

        Returns None if model is not available or loaded.
        """
        if not self._available:
            return None

        if self._session is None:
            try:
                self.load()
            except Exception:
                return None

        # TODO: implement actual inference when model is trained
        # For V1, this is a placeholder that signals unavailability
        return None

    @property
    def stats(self) -> dict:
        return {
            "available": self._available,
            "model_path": str(self._model_path),
            "status": "loaded" if self._session else ("available" if self._available else "not_trained"),
        }
