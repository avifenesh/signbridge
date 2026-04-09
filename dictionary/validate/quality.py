"""Quality validation framework for sign dictionary entries.

Runs automated checks and produces a report for human ASL review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dictionary.config import (
    FACE_EXPRESSION_VALUES,
    HAND_LANDMARK_NAMES,
    JOINT_POSITION_RANGE,
    MAX_SIGN_DURATION_MS,
    MIN_FRAMES_PER_SIGN,
    MIN_SIGN_DURATION_MS,
)


@dataclass
class Issue:
    """A single validation issue."""

    sign_id: str
    severity: str  # "error", "warning", "info"
    check: str
    message: str


@dataclass
class SignScore:
    """Quality score for a single sign."""

    sign_id: str
    gloss: str
    automated_score: float  # 0.0 - 5.0
    issues: list[Issue] = field(default_factory=list)
    human_score: float | None = None  # Set during manual review


@dataclass
class ValidationReport:
    """Complete validation report for a dictionary."""

    scores: list[SignScore] = field(default_factory=list)
    total_entries: int = 0
    passing: int = 0
    failing: int = 0
    warnings: int = 0

    def summary(self) -> str:
        lines = [
            f"Dictionary Validation Report",
            f"============================",
            f"Total entries: {self.total_entries}",
            f"Passing (score >= 3): {self.passing}",
            f"Failing (score < 3):  {self.failing}",
            f"Entries with warnings: {self.warnings}",
            "",
        ]
        if self.failing > 0:
            lines.append("FAILING SIGNS:")
            for s in self.scores:
                if s.automated_score < 3.0:
                    lines.append(f"  {s.sign_id} ({s.gloss}): {s.automated_score:.1f}/5.0")
                    for issue in s.issues:
                        if issue.severity == "error":
                            lines.append(f"    ERROR: {issue.message}")
            lines.append("")

        warning_signs = [s for s in self.scores if any(i.severity == "warning" for i in s.issues)]
        if warning_signs:
            lines.append("WARNINGS:")
            for s in warning_signs:
                for issue in s.issues:
                    if issue.severity == "warning":
                        lines.append(f"  {s.sign_id}: {issue.message}")
            lines.append("")

        return "\n".join(lines)


def _check_joint_ranges(sign: dict) -> list[Issue]:
    """Check that all joint positions are within valid coordinate bounds."""
    issues = []
    lo, hi = JOINT_POSITION_RANGE
    sign_id = sign["sign_id"]

    for i, frame in enumerate(sign.get("frames", [])):
        joints = frame.get("joints", {})
        for joint_name, coords in joints.items():
            if not isinstance(coords, list) or len(coords) != 3:
                issues.append(Issue(
                    sign_id=sign_id,
                    severity="error",
                    check="joint_format",
                    message=f"Frame {i}, joint {joint_name}: expected [x,y,z], got {coords!r}",
                ))
                continue
            for axis, val in zip("xyz", coords):
                if not (lo <= val <= hi):
                    issues.append(Issue(
                        sign_id=sign_id,
                        severity="error",
                        check="joint_range",
                        message=f"Frame {i}, {joint_name}.{axis} = {val} (valid: {lo} to {hi})",
                    ))
    return issues


def _check_timing(sign: dict) -> list[Issue]:
    """Check sign duration and frame timing."""
    issues = []
    sign_id = sign["sign_id"]
    duration = sign.get("duration_ms", 0)
    frames = sign.get("frames", [])
    category = sign.get("category", "sign")

    # Fingerspelling and numbers are single-frame, skip duration checks
    if category in ("fingerspelling", "number"):
        return issues

    if duration < MIN_SIGN_DURATION_MS:
        issues.append(Issue(
            sign_id=sign_id,
            severity="warning",
            check="duration_short",
            message=f"Duration {duration}ms is below minimum {MIN_SIGN_DURATION_MS}ms",
        ))

    if duration > MAX_SIGN_DURATION_MS:
        issues.append(Issue(
            sign_id=sign_id,
            severity="warning",
            check="duration_long",
            message=f"Duration {duration}ms exceeds maximum {MAX_SIGN_DURATION_MS}ms",
        ))

    # Check frame ordering
    times = [f.get("time_ms", 0) for f in frames]
    for i in range(1, len(times)):
        if times[i] <= times[i - 1]:
            issues.append(Issue(
                sign_id=sign_id,
                severity="error",
                check="frame_order",
                message=f"Frame {i} time {times[i]}ms <= previous frame {times[i-1]}ms",
            ))

    return issues


def _check_face_expressions(sign: dict) -> list[Issue]:
    """Check that face expression values are valid."""
    issues = []
    sign_id = sign["sign_id"]

    for i, frame in enumerate(sign.get("frames", [])):
        face = frame.get("face", {})
        for param, value in face.items():
            if param not in FACE_EXPRESSION_VALUES:
                issues.append(Issue(
                    sign_id=sign_id,
                    severity="warning",
                    check="face_unknown_param",
                    message=f"Frame {i}: unknown face parameter {param!r}",
                ))
            elif value not in FACE_EXPRESSION_VALUES[param]:
                issues.append(Issue(
                    sign_id=sign_id,
                    severity="warning",
                    check="face_invalid_value",
                    message=f"Frame {i}: {param}={value!r} not in {FACE_EXPRESSION_VALUES[param]}",
                ))

    return issues


def _check_completeness(sign: dict) -> list[Issue]:
    """Check that the sign has required fields and minimum structure."""
    issues = []
    sign_id = sign.get("sign_id", "UNKNOWN")

    for field_name in ("sign_id", "gloss", "duration_ms", "frames"):
        if field_name not in sign:
            issues.append(Issue(
                sign_id=sign_id,
                severity="error",
                check="missing_field",
                message=f"Missing required field: {field_name}",
            ))

    frames = sign.get("frames", [])
    if len(frames) < 1:
        issues.append(Issue(
            sign_id=sign_id,
            severity="error",
            check="no_frames",
            message="Sign has no frames",
        ))

    # Check that at least one frame has hand data
    has_hands = any(
        f.get("joints", {}).get("right_wrist") or f.get("joints", {}).get("left_wrist")
        for f in frames
    )
    if not has_hands:
        issues.append(Issue(
            sign_id=sign_id,
            severity="error",
            check="no_hand_data",
            message="No hand landmark data found in any frame",
        ))

    return issues


def _check_hand_symmetry(sign: dict) -> list[Issue]:
    """Flag signs where hand data appears/disappears mid-sign (possible tracking loss)."""
    issues = []
    sign_id = sign["sign_id"]
    frames = sign.get("frames", [])

    if len(frames) < 3:
        return issues

    right_present = [bool(f.get("joints", {}).get("right_wrist")) for f in frames]
    left_present = [bool(f.get("joints", {}).get("left_wrist")) for f in frames]

    for hand_name, presence in [("right", right_present), ("left", left_present)]:
        # Check for gaps: present → absent → present
        for i in range(1, len(presence) - 1):
            if not presence[i] and presence[i - 1] and presence[i + 1]:
                issues.append(Issue(
                    sign_id=sign_id,
                    severity="warning",
                    check="tracking_gap",
                    message=f"{hand_name} hand missing in frame {i} but present in adjacent frames",
                ))
                break  # One warning per hand is enough

    return issues


def validate_sign(sign: dict) -> SignScore:
    """Run all automated checks on a single sign entry.

    Returns:
        SignScore with automated_score (0-5) and list of issues.
    """
    sign_id = sign.get("sign_id", "UNKNOWN")
    gloss = sign.get("gloss", "UNKNOWN")

    all_issues = []
    all_issues.extend(_check_completeness(sign))
    all_issues.extend(_check_joint_ranges(sign))
    all_issues.extend(_check_timing(sign))
    all_issues.extend(_check_face_expressions(sign))
    all_issues.extend(_check_hand_symmetry(sign))

    # Score: start at 5, deduct for issues
    score = 5.0
    for issue in all_issues:
        if issue.severity == "error":
            score -= 1.5
        elif issue.severity == "warning":
            score -= 0.5

    score = max(0.0, min(5.0, score))

    return SignScore(
        sign_id=sign_id,
        gloss=gloss,
        automated_score=round(score, 1),
        issues=all_issues,
    )


def validate_dictionary(dictionary: dict) -> ValidationReport:
    """Validate an entire dictionary.

    Args:
        dictionary: Loaded dictionary with "_meta" and "signs" keys.

    Returns:
        ValidationReport with per-sign scores and summary.
    """
    signs = dictionary.get("signs", {})
    report = ValidationReport(total_entries=len(signs))

    for sign_id, sign_data in signs.items():
        score = validate_sign(sign_data)
        report.scores.append(score)
        if score.automated_score >= 3.0:
            report.passing += 1
        else:
            report.failing += 1
        if any(i.severity == "warning" for i in score.issues):
            report.warnings += 1

    return report
