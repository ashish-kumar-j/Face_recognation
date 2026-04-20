from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.deps import get_current_user
from app.models import RecognitionEvent, User
from app.schemas import EventResponse, RecognitionFrameRequest, RecognitionResult
from app.security import decode_session_token
from app.services.recognition import RecognitionService
from app.services.storage import decode_base64_image

router = APIRouter(prefix="/api/recognition", tags=["recognition"])
recognition_service = RecognitionService()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/events", response_model=list[EventResponse])
def list_events(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (
        db.execute(select(RecognitionEvent).order_by(RecognitionEvent.created_at.desc()).limit(100)).scalars().all()
    )
    return [
        EventResponse(
            id=r.id,
            match_status=r.match_status,
            score=r.score,
            liveness_score=r.liveness_score,
            person_id=r.person_id,
            snapshot_path=r.snapshot_path,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/identify", response_model=RecognitionResult)
def identify_face(
    payload: RecognitionFrameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Single-frame recognition endpoint for API clients without WebSocket."""
    try:
        image = decode_base64_image(payload.frame_base64)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image payload: {exc}") from exc

    try:
        return recognition_service.recognize_frame(
            db=db,
            image=image,
            session_key=f"http-{current_user.id}",
        )
    except Exception as exc:
        logger.exception("Recognition failed for HTTP identify endpoint")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="recognition_failed") from exc


@router.websocket("/live")
async def live_recognition_socket(websocket: WebSocket):
    db = SessionLocal()
    try:
        token = websocket.query_params.get("token") or websocket.cookies.get(settings.session_cookie_name)
        if not token:
            await websocket.close(code=4401)
            return

        try:
            payload = decode_session_token(token)
            user_id = int(payload["sub"])
        except Exception:
            await websocket.close(code=4401)
            return

        user = db.get(User, user_id)
        if not user:
            await websocket.close(code=4401)
            return

        await websocket.accept()
        session_key = f"ws-{id(websocket)}-{user.id}"

        while True:
            payload = await websocket.receive_json()
            frame_base64 = payload.get("frame_base64")
            if not frame_base64:
                await websocket.send_json({"error": "Missing frame_base64"})
                continue

            try:
                image = decode_base64_image(frame_base64)
            except Exception as exc:
                await websocket.send_json({"error": f"Invalid image payload: {exc}"})
                continue

            try:
                result = recognition_service.recognize_frame(db=db, image=image, session_key=session_key)
            except Exception:
                logger.exception("Recognition failed for websocket session")
                await websocket.send_json({"error": "recognition_failed"})
                continue

            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        return
    finally:
        db.close()
