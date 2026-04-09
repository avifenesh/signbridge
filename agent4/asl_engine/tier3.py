from __future__ import annotations

from .types import TranslationOutput


class Tier3:
    """Fine-tuned seq2seq model (T5-small ONNX) for English → ASL gloss.

    Stub in V1 — ships only if sufficient training data exists.
    """

    def __init__(self) -> None:
        self.loaded = False

    def translate(self, sentence: str) -> tuple[TranslationOutput | None, bool]:
        if not self.loaded:
            return None, False
        # Future: load ONNX model, run inference, return gloss
        return None, False
