from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np


@dataclass
class FaceFeatures:
    embedding: np.ndarray
    bbox: tuple[int, int, int, int]
    landmarks: np.ndarray | None
    quality_score: float


class FaceEngine:
    def __init__(self) -> None:
        self._insight_model = None
        self._has_insightface = False
        try:
            from insightface.app import FaceAnalysis  # type: ignore

            model = FaceAnalysis(name="buffalo_l")
            model.prepare(ctx_id=-1)
            self._insight_model = model
            self._has_insightface = True
        except Exception:
            self._insight_model = None
            self._has_insightface = False

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._haar = cv2.CascadeClassifier(cascade_path)

    def detect_faces(self, image: np.ndarray) -> list[FaceFeatures]:
        if self._has_insightface and self._insight_model is not None:
            return self._detect_with_insightface(image)
        return self._detect_with_fallback(image)

    def _detect_with_insightface(self, image: np.ndarray) -> list[FaceFeatures]:
        faces = self._insight_model.get(image)
        results: list[FaceFeatures] = []
        for face in faces:
            bbox = tuple(int(v) for v in face.bbox.tolist())
            landmark = np.array(face.kps, dtype=np.float32) if getattr(face, "kps", None) is not None else None
            emb = np.array(face.embedding, dtype=np.float32)
            quality = float(face.det_score) if getattr(face, "det_score", None) is not None else 1.0
            results.append(FaceFeatures(embedding=emb, bbox=bbox, landmarks=landmark, quality_score=quality))
        return results

    def _detect_with_fallback(self, image: np.ndarray) -> list[FaceFeatures]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        boxes = self._haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        if len(boxes) == 0:
            h, w = gray.shape
            boxes = np.array([[0, 0, w, h]])

        results: list[FaceFeatures] = []
        for (x, y, w, h) in boxes:
            crop = gray[y : y + h, x : x + w]
            if crop.size == 0:
                continue
            emb = self._fallback_embedding(crop)
            bbox = (int(x), int(y), int(x + w), int(y + h))
            quality = float(min(1.0, max(0.1, np.std(crop) / 64.0)))
            results.append(FaceFeatures(embedding=emb, bbox=bbox, landmarks=None, quality_score=quality))
        return results

    def _fallback_embedding(self, face_crop_gray: np.ndarray) -> np.ndarray:
        resized = cv2.resize(face_crop_gray, (32, 32), interpolation=cv2.INTER_AREA)
        normalized = resized.astype(np.float32) / 255.0

        pooled = normalized.reshape(16, 2, 16, 2).mean(axis=(1, 3)).reshape(-1)
        fft = np.fft.rfft(normalized.flatten(), n=256)
        spectral = np.abs(fft)[:64].astype(np.float32)

        combined = np.concatenate([pooled.astype(np.float32), spectral])
        if combined.shape[0] < 128:
            combined = np.pad(combined, (0, 128 - combined.shape[0]))
        else:
            combined = combined[:128]

        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined.astype(np.float32)


@lru_cache(maxsize=1)
def get_face_engine() -> FaceEngine:
    return FaceEngine()
