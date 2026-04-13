from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import enforce_csrf, require_admin
from app.models import WebhookOutbox, User
from app.schemas import WebhookOutboxResponse

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.get("/outbox", response_model=list[WebhookOutboxResponse])
def get_outbox(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(select(WebhookOutbox).order_by(WebhookOutbox.created_at.desc()).limit(200)).scalars().all()
    return [
        WebhookOutboxResponse(
            id=r.id,
            recognition_event_id=r.recognition_event_id,
            status=r.status,
            retry_count=r.retry_count,
            next_retry_at=r.next_retry_at,
            last_error=r.last_error,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/outbox/{outbox_id}/retry")
def retry_outbox(
    outbox_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    row = db.get(WebhookOutbox, outbox_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbox item not found")

    row.status = "pending"
    row.next_retry_at = datetime.now(timezone.utc)
    row.last_error = None
    db.commit()
    return {"ok": True}
