from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LivenessResult:
    passed: bool
    score: float
    reason: str


class LivenessAnalyzer:
    """Basic liveness heuristic using face motion and simple eye landmark signal."""

    def __init__(self) -> None:
        self._state: dict[str, dict[str, float]] = {}

    def evaluate(
        self,
        session_key: str,
        bbox: tuple[int, int, int, int],
        landmarks: np.ndarray | None,
    ) -> LivenessResult:
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        area = max(1.0, float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])))

        prev = self._state.get(session_key)
        motion = 0.0
        if prev:
            dx = cx - prev["cx"]
            dy = cy - prev["cy"]
            motion = (dx * dx + dy * dy) ** 0.5 / max(1.0, area**0.5)

        eye_signal = self._eye_signal(landmarks)
        motion_component = min(1.0, motion * 4.0)
        eye_component = min(1.0, eye_signal * 2.5)
        score = min(1.0, 0.6 * motion_component + 0.4 * eye_component)

        self._state[session_key] = {
            "cx": cx,
            "cy": cy,
            "area": area,
            "eye_signal": eye_signal,
        }

        if score >= 0.45:
            return LivenessResult(passed=True, score=score, reason="motion/eye-signal ok")
        if motion_component < 0.1 and eye_component < 0.1:
            return LivenessResult(passed=False, score=score, reason="insufficient liveness cues")
        return LivenessResult(passed=False, score=score, reason="weak liveness signal")

    @staticmethod
    def _eye_signal(landmarks: np.ndarray | None) -> float:
        if landmarks is None or len(landmarks) < 2:
            return 0.0
        try:
            left_eye = landmarks[0]
            right_eye = landmarks[1]
            eye_distance = float(np.linalg.norm(left_eye - right_eye))
            return min(1.0, eye_distance / 90.0)
        except Exception:
            return 0.0
