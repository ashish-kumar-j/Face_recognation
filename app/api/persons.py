from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import enforce_csrf, require_admin
from app.models import Person, User
from app.schemas import CameraEnrollmentRequest, PersonCreateRequest, PersonResponse
from app.services.recognition import RecognitionService
from app.services.storage import decode_base64_image

router = APIRouter(prefix="/api/persons", tags=["persons"])
recognition_service = RecognitionService()


@router.post("", response_model=PersonResponse)
def create_person(
    payload: PersonCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    person = Person(display_name=payload.display_name.strip(), external_id=payload.external_id, active=True)
    db.add(person)
    db.commit()
    db.refresh(person)
    return PersonResponse(id=person.id, display_name=person.display_name, external_id=person.external_id, active=person.active)


@router.get("", response_model=list[PersonResponse])
def list_persons(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(select(Person).where(Person.active.is_(True)).order_by(Person.display_name.asc())).scalars().all()
    return [PersonResponse(id=r.id, display_name=r.display_name, external_id=r.external_id, active=r.active) for r in rows]


@router.delete("/{person_id}")
def deactivate_person(
    person_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    person.active = False
    db.commit()
    return {"ok": True}


@router.post("/{person_id}/enroll/camera")
def enroll_camera(
    person_id: int,
    payload: CameraEnrollmentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    image = decode_base64_image(payload.frame_base64)
    sample, embedding = recognition_service.enroll_from_image(db, person_id, image, source="camera")
    return {
        "sample_id": sample.id,
        "embedding_id": embedding.id,
        "quality_score": sample.quality_score,
    }


@router.post("/{person_id}/enroll/upload")
async def enroll_upload(
    person_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")

    import base64

    encoded = base64.b64encode(blob).decode("ascii")
    image = decode_base64_image(encoded)
    sample, embedding = recognition_service.enroll_from_image(db, person_id, image, source="upload")
    return {
        "sample_id": sample.id,
        "embedding_id": embedding.id,
        "quality_score": sample.quality_score,
    }
