"""Shared data types for the dictionary pipeline.

Kept separate from mediapipe.py so modules that only need the types
don't pull in cv2/mediapipe dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawFrame:
    """Raw extracted landmarks for a single video frame."""

    time_ms: float
    left_hand: dict[str, list[float]] | None = None   # landmark_name → [x, y, z]
    right_hand: dict[str, list[float]] | None = None
    body: dict[str, list[float]] | None = None         # joint_name → [x, y, z]
    face: dict[str, str] | None = None                 # param_name → value


@dataclass
class ExtractionResult:
    """Complete extraction from a single video."""

    sign_id: str
    gloss: str
    source_path: str
    fps: float
    total_frames: int
    frames: list[RawFrame] = field(default_factory=list)
