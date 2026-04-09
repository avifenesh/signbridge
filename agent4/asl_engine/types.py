from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SignType(str, Enum):
    SIGN = "sign"
    FINGERSPELL = "fingerspell"


@dataclass
class STTOutput:
    sentence: str
    confidence: float
    source: str


@dataclass
class TranslationOutput:
    asl_gloss: list[str]
    method: str
    pattern: str = ""
    confidence: float = 0.0


@dataclass
class SignEntry:
    gloss: str
    type: SignType
    duration_ms: int
    sign_id: str = ""
    letters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "gloss": self.gloss,
            "type": self.type.value,
            "duration_ms": self.duration_ms,
        }
        if self.type == SignType.SIGN:
            d["sign_id"] = self.sign_id
        if self.type == SignType.FINGERSPELL:
            d["letters"] = self.letters
        return d


@dataclass
class SignSequence:
    type: str
    english: str
    pipeline_confidence: float
    gloss: list[str]
    signs: list[SignEntry]

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "english": self.english,
            "pipeline_confidence": round(self.pipeline_confidence, 4),
            "gloss": self.gloss,
            "signs": [s.to_dict() for s in self.signs],
        }


class LowConfidenceError(Exception):
    def __init__(self, sentence: str, confidence: float, threshold: float):
        self.sentence = sentence
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"stt confidence {confidence:.2f} below threshold {threshold:.2f}: {sentence}"
        )
