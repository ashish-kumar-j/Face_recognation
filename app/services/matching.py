from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def best_match(query: np.ndarray, known_embeddings: list[tuple[int, str, np.ndarray]]) -> tuple[int | None, str | None, float]:
    best_person_id: int | None = None
    best_person_name: str | None = None
    best_score = -1.0

    for person_id, person_name, emb in known_embeddings:
        score = cosine_similarity(query, emb)
        if score > best_score:
            best_person_id = person_id
            best_person_name = person_name
            best_score = score

    if best_score < 0:
        return None, None, 0.0
    return best_person_id, best_person_name, best_score
