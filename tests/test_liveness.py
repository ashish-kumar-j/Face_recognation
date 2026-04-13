from __future__ import annotations

import numpy as np

from app.services.liveness import LivenessAnalyzer


def test_liveness_passes_after_motion_signal():
    analyzer = LivenessAnalyzer()

    first = analyzer.evaluate("s1", (0, 0, 100, 100), np.array([[20, 20], [80, 20]], dtype=np.float32))
    second = analyzer.evaluate("s1", (15, 10, 115, 110), np.array([[22, 21], [82, 21]], dtype=np.float32))

    assert first.passed is False
    assert second.passed is True
    assert second.score > first.score


def test_liveness_fails_with_static_no_landmark_signal():
    analyzer = LivenessAnalyzer()
    analyzer.evaluate("s2", (10, 10, 110, 110), None)
    result = analyzer.evaluate("s2", (10, 10, 110, 110), None)
    assert result.passed is False
