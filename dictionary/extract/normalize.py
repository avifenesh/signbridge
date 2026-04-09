"""Normalize extracted landmarks to a consistent coordinate space."""

from __future__ import annotations

import copy
import math

import numpy as np

from dictionary.config import (
    JOINT_POSITION_RANGE,
    NORMALIZE_REFERENCE_JOINT,
    NORMALIZE_SCALE_JOINTS,
)
from dictionary.types import ExtractionResult, RawFrame


def _get_body_point(frame: RawFrame, joint_name: str) -> np.ndarray | None:
    """Get a body joint as numpy array, or None if missing."""
    if frame.body and joint_name in frame.body:
        return np.array(frame.body[joint_name])
    return None


def _translate_points(points: dict[str, list[float]], origin: np.ndarray) -> dict[str, list[float]]:
    """Translate all points by subtracting origin."""
    return {
        name: [round(v - o, 6) for v, o in zip(coords, origin)]
        for name, coords in points.items()
    }


def _scale_points(points: dict[str, list[float]], scale: float) -> dict[str, list[float]]:
    """Scale all points by a factor."""
    return {
        name: [round(v * scale, 6) for v in coords]
        for name, coords in points.items()
    }


def _clamp_points(points: dict[str, list[float]], lo: float, hi: float) -> dict[str, list[float]]:
    """Clamp all coordinates to [lo, hi]."""
    return {
        name: [round(max(lo, min(hi, v)), 6) for v in coords]
        for name, coords in points.items()
    }


def normalize_frame(frame: RawFrame, origin: np.ndarray, scale: float) -> RawFrame:
    """Normalize a single frame's landmarks.

    - Translates so origin joint is at (0, 0, 0)
    - Scales so reference distance = 1.0
    - Clamps to valid range
    """
    lo, hi = JOINT_POSITION_RANGE
    out = RawFrame(time_ms=frame.time_ms, face=frame.face)

    if frame.left_hand:
        pts = _translate_points(frame.left_hand, origin)
        pts = _scale_points(pts, scale)
        out.left_hand = _clamp_points(pts, lo, hi)

    if frame.right_hand:
        pts = _translate_points(frame.right_hand, origin)
        pts = _scale_points(pts, scale)
        out.right_hand = _clamp_points(pts, lo, hi)

    if frame.body:
        pts = _translate_points(frame.body, origin)
        pts = _scale_points(pts, scale)
        out.body = _clamp_points(pts, lo, hi)

    return out


def compute_normalization_params(
    result: ExtractionResult,
) -> tuple[np.ndarray, float]:
    """Compute origin and scale from the median body position across all frames.

    Returns:
        (origin, scale) where origin is the median reference joint position
        and scale normalizes the shoulder distance to 1.0.
    """
    ref_joint = NORMALIZE_REFERENCE_JOINT
    scale_a, scale_b = NORMALIZE_SCALE_JOINTS

    origins = []
    distances = []

    for frame in result.frames:
        origin_pt = _get_body_point(frame, ref_joint)
        a_pt = _get_body_point(frame, scale_a)
        b_pt = _get_body_point(frame, scale_b)
        if origin_pt is not None:
            origins.append(origin_pt)
        if a_pt is not None and b_pt is not None:
            dist = float(np.linalg.norm(a_pt - b_pt))
            if dist > 0.001:
                distances.append(dist)

    if not origins:
        # No body data — use zero origin, unit scale
        return np.array([0.0, 0.0, 0.0]), 1.0

    origin = np.median(origins, axis=0)
    scale = 1.0 / np.median(distances) if distances else 1.0
    return origin, scale


def normalize_extraction(result: ExtractionResult) -> ExtractionResult:
    """Normalize all frames in an extraction result.

    Coordinates are translated so the reference joint (right_shoulder) is at
    the origin, and scaled so shoulder width = 1.0. This makes signs
    comparable regardless of the signer's distance from the camera.
    """
    origin, scale = compute_normalization_params(result)

    normalized = ExtractionResult(
        sign_id=result.sign_id,
        gloss=result.gloss,
        source_path=result.source_path,
        fps=result.fps,
        total_frames=result.total_frames,
    )
    normalized.frames = [normalize_frame(f, origin, scale) for f in result.frames]
    return normalized
