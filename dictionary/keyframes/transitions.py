"""Extract and store transition paths between sign pairs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from dictionary.types import RawFrame


@dataclass
class TransitionPath:
    """A transition path between two signs.

    Stores intermediate poses that should be followed when transitioning
    from sign_a to sign_b, instead of simple slerp interpolation.
    """

    sign_a_id: str
    sign_b_id: str
    duration_ms: int
    waypoints: list[RawFrame] = field(default_factory=list)


def extract_transition(
    sign_a_frames: list[RawFrame],
    sign_b_frames: list[RawFrame],
    sign_a_id: str,
    sign_b_id: str,
    *,
    num_waypoints: int = 3,
) -> TransitionPath:
    """Generate a transition path between two signs.

    Takes the last frame of sign A and first frame of sign B,
    and creates intermediate waypoints using spline interpolation
    on the joint positions.

    Args:
        sign_a_frames: Keyframes of the first sign.
        sign_b_frames: Keyframes of the second sign.
        sign_a_id: ID of the first sign.
        sign_b_id: ID of the second sign.
        num_waypoints: Number of intermediate poses to generate.

    Returns:
        TransitionPath with interpolated waypoints.
    """
    if not sign_a_frames or not sign_b_frames:
        return TransitionPath(sign_a_id=sign_a_id, sign_b_id=sign_b_id, duration_ms=100)

    end_frame = sign_a_frames[-1]
    start_frame = sign_b_frames[0]

    waypoints = []
    for i in range(1, num_waypoints + 1):
        t = i / (num_waypoints + 1)  # 0 < t < 1
        wp = _interpolate_frame(end_frame, start_frame, t)
        waypoints.append(wp)

    # Estimate duration based on movement distance
    distance = _frame_distance(end_frame, start_frame)
    duration_ms = max(50, min(300, int(distance * 500)))

    return TransitionPath(
        sign_a_id=sign_a_id,
        sign_b_id=sign_b_id,
        duration_ms=duration_ms,
        waypoints=waypoints,
    )


def _interpolate_points(
    a: dict[str, list[float]] | None,
    b: dict[str, list[float]] | None,
    t: float,
) -> dict[str, list[float]] | None:
    """Linearly interpolate between two point dicts."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a

    result = {}
    all_keys = set(a.keys()) | set(b.keys())
    for key in all_keys:
        a_val = a.get(key, [0.0, 0.0, 0.0])
        b_val = b.get(key, [0.0, 0.0, 0.0])
        result[key] = [round(a_v + t * (b_v - a_v), 6) for a_v, b_v in zip(a_val, b_val)]
    return result


def _interpolate_face(
    a: dict[str, str] | None,
    b: dict[str, str] | None,
    t: float,
) -> dict[str, str] | None:
    """Interpolate face expressions — snap to target at t=0.5."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return a if t < 0.5 else b


def _interpolate_frame(a: RawFrame, b: RawFrame, t: float) -> RawFrame:
    """Interpolate between two frames at parameter t in [0, 1]."""
    return RawFrame(
        time_ms=round(a.time_ms + t * (b.time_ms - a.time_ms), 1),
        left_hand=_interpolate_points(a.left_hand, b.left_hand, t),
        right_hand=_interpolate_points(a.right_hand, b.right_hand, t),
        body=_interpolate_points(a.body, b.body, t),
        face=_interpolate_face(a.face, b.face, t),
    )


def _frame_distance(a: RawFrame, b: RawFrame) -> float:
    """Compute the L2 distance between two frames' hand positions."""
    dist = 0.0
    for hand_attr in ("right_hand", "left_hand"):
        a_hand = getattr(a, hand_attr)
        b_hand = getattr(b, hand_attr)
        if a_hand and b_hand:
            for key in set(a_hand.keys()) & set(b_hand.keys()):
                a_v = np.array(a_hand[key])
                b_v = np.array(b_hand[key])
                dist += float(np.linalg.norm(a_v - b_v))
    return dist


def transition_to_dict(tp: TransitionPath) -> dict:
    """Serialize a TransitionPath to a dictionary."""
    return {
        "sign_a": tp.sign_a_id,
        "sign_b": tp.sign_b_id,
        "duration_ms": tp.duration_ms,
        "waypoints": [
            {
                "time_ms": wp.time_ms,
                **({"left_hand": wp.left_hand} if wp.left_hand else {}),
                **({"right_hand": wp.right_hand} if wp.right_hand else {}),
                **({"body": wp.body} if wp.body else {}),
                **({"face": wp.face} if wp.face else {}),
            }
            for wp in tp.waypoints
        ],
    }
