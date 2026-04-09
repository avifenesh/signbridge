"""Select keyframes from continuous extraction data using velocity-based peak detection."""

from __future__ import annotations

import numpy as np

from dictionary.config import (
    MAX_KEYFRAME_INTERVAL_MS,
    MIN_KEYFRAME_INTERVAL_MS,
    VELOCITY_THRESHOLD,
)
from dictionary.types import ExtractionResult, RawFrame


def _frame_to_vector(frame: RawFrame) -> np.ndarray | None:
    """Flatten a frame's spatial landmarks into a single vector for velocity computation.

    Only includes hand and body points (not face — face expressions are discrete).
    """
    parts = []
    for hand in (frame.right_hand, frame.left_hand):
        if hand:
            for coords in hand.values():
                parts.extend(coords)
        else:
            # Pad with zeros to keep vector length consistent
            parts.extend([0.0] * (21 * 3))
    if frame.body:
        for coords in frame.body.values():
            parts.extend(coords)
    else:
        parts.extend([0.0] * (6 * 3))

    if not any(v != 0.0 for v in parts):
        return None
    return np.array(parts)


def _compute_velocities(frames: list[RawFrame]) -> list[float]:
    """Compute frame-to-frame velocity (L2 distance of landmark movement)."""
    vectors = [_frame_to_vector(f) for f in frames]
    velocities = [0.0]  # first frame has zero velocity
    for i in range(1, len(vectors)):
        if vectors[i] is not None and vectors[i - 1] is not None:
            velocities.append(float(np.linalg.norm(vectors[i] - vectors[i - 1])))
        else:
            velocities.append(0.0)
    return velocities


def select_keyframes(result: ExtractionResult) -> list[RawFrame]:
    """Select keyframes from an extraction result.

    Strategy:
    - Always include first and last frames
    - Include frames at velocity peaks (direction changes in movement)
    - Include frames at velocity valleys (hold positions — important in ASL)
    - Force a keyframe if none selected for MAX_KEYFRAME_INTERVAL_MS
    - Skip keyframes closer than MIN_KEYFRAME_INTERVAL_MS

    Returns:
        List of selected RawFrame objects with original time_ms preserved.
    """
    frames = result.frames
    if len(frames) <= 3:
        return list(frames)

    velocities = _compute_velocities(frames)
    selected_indices: set[int] = {0, len(frames) - 1}

    # Find velocity peaks and valleys (direction changes)
    for i in range(1, len(velocities) - 1):
        prev_v = velocities[i - 1]
        curr_v = velocities[i]
        next_v = velocities[i + 1]

        is_peak = curr_v > prev_v and curr_v > next_v and curr_v > VELOCITY_THRESHOLD
        is_valley = curr_v < prev_v and curr_v < next_v and prev_v > VELOCITY_THRESHOLD

        if is_peak or is_valley:
            selected_indices.add(i)

    # Sort by index
    sorted_indices = sorted(selected_indices)

    # Enforce minimum spacing
    filtered = [sorted_indices[0]]
    for idx in sorted_indices[1:]:
        prev_time = frames[filtered[-1]].time_ms
        curr_time = frames[idx].time_ms
        if curr_time - prev_time >= MIN_KEYFRAME_INTERVAL_MS:
            filtered.append(idx)
    # Always include last
    if filtered[-1] != sorted_indices[-1]:
        filtered.append(sorted_indices[-1])

    # Enforce maximum gap — insert keyframes where gaps are too large
    final = [filtered[0]]
    for i in range(1, len(filtered)):
        prev_idx = final[-1]
        curr_idx = filtered[i]
        prev_time = frames[prev_idx].time_ms
        curr_time = frames[curr_idx].time_ms

        if curr_time - prev_time > MAX_KEYFRAME_INTERVAL_MS:
            # Fill the gap with evenly spaced keyframes
            gap_ms = curr_time - prev_time
            num_fill = int(gap_ms / MAX_KEYFRAME_INTERVAL_MS)
            for j in range(1, num_fill + 1):
                target_time = prev_time + j * (gap_ms / (num_fill + 1))
                # Find closest frame to target time
                best_idx = prev_idx
                best_diff = float("inf")
                for k in range(prev_idx + 1, curr_idx):
                    diff = abs(frames[k].time_ms - target_time)
                    if diff < best_diff:
                        best_diff = diff
                        best_idx = k
                if best_idx != final[-1]:
                    final.append(best_idx)

        final.append(curr_idx)

    return [frames[i] for i in sorted(set(final))]


def reindex_keyframes(keyframes: list[RawFrame]) -> list[RawFrame]:
    """Reindex keyframe times to start at 0 and preserve relative spacing."""
    if not keyframes:
        return []
    base_time = keyframes[0].time_ms
    reindexed = []
    for kf in keyframes:
        new_kf = RawFrame(
            time_ms=round(kf.time_ms - base_time, 1),
            left_hand=kf.left_hand,
            right_hand=kf.right_hand,
            body=kf.body,
            face=kf.face,
        )
        reindexed.append(new_kf)
    return reindexed
