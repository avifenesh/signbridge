"""Extract hand, pose, and face landmarks from video using MediaPipe."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from dictionary.config import (
    FACE_EXPRESSION_VALUES,
    FACE_PARAMS,
    HAND_LANDMARK_NAMES,
)
from dictionary.types import ExtractionResult, RawFrame


def _landmarks_to_dict(landmarks, names: list[str]) -> dict[str, list[float]]:
    """Convert MediaPipe landmark list to {name: [x, y, z]} dict."""
    result = {}
    for i, name in enumerate(names):
        if i < len(landmarks.landmark):
            lm = landmarks.landmark[i]
            result[name] = [round(lm.x, 6), round(lm.y, 6), round(lm.z, 6)]
    return result


def _classify_face(face_landmarks) -> dict[str, str]:
    """Derive facial expression parameters from face mesh landmarks.

    Uses key landmark positions to estimate discrete expression states.
    This is approximate — fine-tuning thresholds against real ASL data is needed.
    """
    lm = face_landmarks.landmark

    # Eyebrows: compare brow landmarks (65, 295) Y vs eye landmarks (159, 386) Y
    # Lower Y = higher on screen in MediaPipe's coordinate system (0=top)
    brow_y = (lm[65].y + lm[295].y) / 2
    eye_y = (lm[159].y + lm[386].y) / 2
    brow_dist = eye_y - brow_y
    if brow_dist > 0.06:
        eyebrows = "raised"
    elif brow_dist < 0.03:
        eyebrows = "furrowed"
    else:
        eyebrows = "neutral"

    # Mouth: distance between upper lip (13) and lower lip (14)
    mouth_open = abs(lm[14].y - lm[13].y)
    # Width: distance between mouth corners (61, 291)
    mouth_width = abs(lm[291].x - lm[61].x)
    if mouth_open > 0.04:
        mouth = "open_wide"
    elif mouth_open > 0.02:
        mouth = "open_slight"
    elif mouth_width > 0.12:
        # Check if corners are above midline for smile
        mid_y = (lm[13].y + lm[14].y) / 2
        if (lm[61].y + lm[291].y) / 2 < mid_y:
            mouth = "smile"
        else:
            mouth = "frown"
    elif mouth_open > 0.015 and mouth_width < 0.08:
        mouth = "rounded"
    else:
        mouth = "closed"

    # Head tilt: use nose tip (1) relative to face center approximation
    nose = lm[1]
    forehead = lm[10]
    chin = lm[152]
    face_center_x = (lm[234].x + lm[454].x) / 2
    tilt_x = nose.x - face_center_x
    tilt_y = nose.y - (forehead.y + chin.y) / 2
    if abs(tilt_x) > 0.03:
        head_tilt = "left" if tilt_x < 0 else "right"
    elif tilt_y < -0.05:
        head_tilt = "back"
    elif tilt_y > 0.05:
        head_tilt = "forward"
    else:
        head_tilt = "neutral"

    # Eye gaze: compare iris center to eye center
    # Left iris (468-472), left eye corners (33, 133)
    if len(lm) > 472:
        iris_x = lm[468].x
        eye_left = lm[33].x
        eye_right = lm[133].x
        eye_center_x = (eye_left + eye_right) / 2
        iris_y = lm[468].y
        eye_top = lm[159].y
        eye_bottom = lm[145].y
        eye_center_y = (eye_top + eye_bottom) / 2

        gaze_x = iris_x - eye_center_x
        gaze_y = iris_y - eye_center_y
        if abs(gaze_x) > 0.01:
            eye_gaze = "left" if gaze_x < 0 else "right"
        elif abs(gaze_y) > 0.008:
            eye_gaze = "up" if gaze_y < 0 else "down"
        else:
            eye_gaze = "center"
    else:
        eye_gaze = "center"

    # Cheek puff: approximate from cheek landmark spread
    left_cheek = lm[234]
    right_cheek = lm[454]
    cheek_width = abs(right_cheek.x - left_cheek.x)
    cheek_puff = "puffed" if cheek_width > 0.38 else "neutral"

    return {
        "eyebrows": eyebrows,
        "mouth": mouth,
        "head_tilt": head_tilt,
        "eye_gaze": eye_gaze,
        "cheek_puff": cheek_puff,
    }


# MediaPipe pose landmark indices for upper body
_POSE_JOINT_MAP = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
}


def extract_video(
    video_path: str | Path,
    sign_id: str,
    gloss: str,
    *,
    max_frames: int = 0,
) -> ExtractionResult:
    """Extract landmarks from a video file.

    Args:
        video_path: Path to the video file.
        sign_id: Unique identifier for this sign (e.g., "book").
        gloss: ASL gloss label (e.g., "BOOK").
        max_frames: If > 0, stop after this many frames.

    Returns:
        ExtractionResult with all extracted frames.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ms_per_frame = 1000.0 / fps

    mp_hands = mp.solutions.hands
    mp_pose = mp.solutions.pose
    mp_face = mp.solutions.face_mesh

    result = ExtractionResult(
        sign_id=sign_id,
        gloss=gloss,
        source_path=str(video_path),
        fps=fps,
        total_frames=total_frames,
    )

    with (
        mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as hands,
        mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose,
        mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # enables iris landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as face_mesh,
    ):
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if max_frames > 0 and frame_idx >= max_frames:
                break

            time_ms = round(frame_idx * ms_per_frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            raw = RawFrame(time_ms=time_ms)

            # Hands
            hand_results = hands.process(rgb)
            if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
                for hand_lm, handedness in zip(
                    hand_results.multi_hand_landmarks,
                    hand_results.multi_handedness,
                ):
                    label = handedness.classification[0].label  # "Left" or "Right"
                    d = _landmarks_to_dict(hand_lm, HAND_LANDMARK_NAMES)
                    # MediaPipe mirrors: "Left" in results = signer's right hand when facing camera
                    if label == "Left":
                        raw.right_hand = d
                    else:
                        raw.left_hand = d

            # Pose (upper body)
            pose_results = pose.process(rgb)
            if pose_results.pose_landmarks:
                body = {}
                for joint_name, idx in _POSE_JOINT_MAP.items():
                    lm = pose_results.pose_landmarks.landmark[idx]
                    body[joint_name] = [round(lm.x, 6), round(lm.y, 6), round(lm.z, 6)]
                raw.body = body

            # Face
            face_results = face_mesh.process(rgb)
            if face_results.multi_face_landmarks:
                raw.face = _classify_face(face_results.multi_face_landmarks[0])

            result.frames.append(raw)
            frame_idx += 1

    cap.release()
    return result


def extraction_to_dict(result: ExtractionResult) -> dict:
    """Convert ExtractionResult to a serializable dictionary."""
    frames = []
    for f in result.frames:
        fd = {"time_ms": f.time_ms}
        if f.left_hand:
            fd["left_hand"] = f.left_hand
        if f.right_hand:
            fd["right_hand"] = f.right_hand
        if f.body:
            fd["body"] = f.body
        if f.face:
            fd["face"] = f.face
        frames.append(fd)
    return {
        "sign_id": result.sign_id,
        "gloss": result.gloss,
        "source_path": result.source_path,
        "fps": result.fps,
        "total_frames": result.total_frames,
        "frames": frames,
    }


def save_extraction(result: ExtractionResult, output_path: str | Path) -> None:
    """Save extraction result to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(extraction_to_dict(result), f, indent=2)
