from __future__ import annotations

import numpy as np

from app.services.matching import best_match, cosine_similarity


def test_cosine_similarity_identical_vectors():
    a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    b = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-6


def test_best_match_returns_expected_identity():
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    known = [
        (1, "alice", np.array([1.0, 0.0, 0.0], dtype=np.float32)),
        (2, "bob", np.array([0.0, 1.0, 0.0], dtype=np.float32)),
    ]

    person_id, person_name, score = best_match(query, known)
    assert person_id == 1
    assert person_name == "alice"
    assert score > 0.99
