from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting, FaceEmbedding, FaceSample, Person, RecognitionEvent
from app.schemas import RecognitionResult
from app.services.face_engine import FaceFeatures, get_face_engine
from app.services.liveness import LivenessAnalyzer
from app.services.matching import best_match
from app.services.storage import save_image
from app.services.webhook import enqueue_event_webhook


@dataclass
class RecognitionDependencies:
    liveness: LivenessAnalyzer


class RecognitionService:
    def __init__(self, deps: RecognitionDependencies | None = None) -> None:
        self.face_engine = get_face_engine()
        self.liveness = deps.liveness if deps else LivenessAnalyzer()

    def enroll_from_image(self, db: Session, person_id: int, image: np.ndarray, source: str) -> tuple[FaceSample, FaceEmbedding]:
        person = db.get(Person, person_id)
        if not person or not person.active:
            raise ValueError("Person not found")

        faces = self.face_engine.detect_faces(image)
        if not faces:
            raise ValueError("No face found in image")

        face = max(faces, key=lambda item: item.quality_score)
        image_path = save_image(image, "sample")

        sample = FaceSample(person_id=person_id, source=source, image_path=image_path, quality_score=face.quality_score)
        db.add(sample)
        db.commit()
        db.refresh(sample)

        embedding = FaceEmbedding(
            person_id=person_id,
            sample_id=sample.id,
            embedding_json=json.dumps(face.embedding.tolist(), separators=(",", ":")),
            model_version="insightface-v1",
        )
        db.add(embedding)
        db.commit()
        db.refresh(embedding)
        return sample, embedding

    def recognize_frame(
        self,
        db: Session,
        image: np.ndarray,
        session_key: str,
    ) -> RecognitionResult:
        settings = self._get_settings(db)
        faces = self.face_engine.detect_faces(image)

        if not faces:
            event = self._log_event(db, "unknown", None, None, None, None)
            enqueue_event_webhook(db, event, settings)
            return RecognitionResult(
                match_status="unknown",
                threshold=settings.strict_match_threshold,
                message="No detectable face",
            )

        face = max(faces, key=lambda f: f.quality_score)
        known_embeddings = self._load_embeddings(db)
        person_id, person_name, score = best_match(face.embedding, known_embeddings)

        liveness_result = self.liveness.evaluate(session_key=session_key, bbox=face.bbox, landmarks=face.landmarks)
        liveness_score = liveness_result.score

        snapshot_path = None
        if person_id is not None and score >= settings.strict_match_threshold:
            if not liveness_result.passed:
                if settings.store_unknown_snapshots:
                    snapshot_path = save_image(image, "snapshot")
                event = self._log_event(db, "rejected_liveness", score, liveness_score, None, snapshot_path)
                enqueue_event_webhook(db, event, settings)
                return RecognitionResult(
                    match_status="rejected_liveness",
                    person_id=person_id,
                    person_name=person_name,
                    score=score,
                    liveness_score=liveness_score,
                    threshold=settings.strict_match_threshold,
                    message="Match rejected due to liveness",
                )

            if settings.store_known_snapshots:
                snapshot_path = save_image(image, "snapshot")
            event = self._log_event(db, "known", score, liveness_score, person_id, snapshot_path)
            enqueue_event_webhook(db, event, settings)
            return RecognitionResult(
                match_status="known",
                person_id=person_id,
                person_name=person_name,
                score=score,
                liveness_score=liveness_score,
                threshold=settings.strict_match_threshold,
                message="Known face identified",
            )

        if settings.store_unknown_snapshots:
            snapshot_path = save_image(image, "snapshot")
        event = self._log_event(db, "unknown", score if person_id else None, liveness_score, None, snapshot_path)
        enqueue_event_webhook(db, event, settings)

        return RecognitionResult(
            match_status="unknown",
            score=score if person_id else None,
            liveness_score=liveness_score,
            threshold=settings.strict_match_threshold,
            message="No strict match",
        )

    def _load_embeddings(self, db: Session) -> list[tuple[int, str, np.ndarray]]:
        stmt = (
            select(FaceEmbedding.person_id, Person.display_name, FaceEmbedding.embedding_json)
            .join(Person, Person.id == FaceEmbedding.person_id)
            .where(Person.active.is_(True))
        )
        rows = db.execute(stmt).all()
        known: list[tuple[int, str, np.ndarray]] = []
        for person_id, person_name, embedding_json in rows:
            emb = np.array(json.loads(embedding_json), dtype=np.float32)
            known.append((person_id, person_name, emb))
        return known

    def _log_event(
        self,
        db: Session,
        status: str,
        score: float | None,
        liveness_score: float | None,
        person_id: int | None,
        snapshot_path: str | None,
    ) -> RecognitionEvent:
        event = RecognitionEvent(
            match_status=status,
            score=score,
            liveness_score=liveness_score,
            person_id=person_id,
            snapshot_path=snapshot_path,
            metadata_json=None,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def _get_settings(db: Session) -> AppSetting:
        settings = db.execute(select(AppSetting).where(AppSetting.singleton_key == "default")).scalar_one()
        return settings
