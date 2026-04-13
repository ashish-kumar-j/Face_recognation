from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting, RecognitionEvent, WebhookOutbox


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sign_payload(payload_json: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def enqueue_event_webhook(db: Session, event: RecognitionEvent, settings: AppSetting) -> WebhookOutbox | None:
    if not settings.webhook_url or not settings.webhook_secret:
        return None

    payload = {
        "event_id": event.id,
        "match_status": event.match_status,
        "score": event.score,
        "liveness_score": event.liveness_score,
        "person_id": event.person_id,
        "snapshot_path": event.snapshot_path,
        "created_at": event.created_at.isoformat(),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    signature = sign_payload(payload_json, settings.webhook_secret)

    outbox = WebhookOutbox(
        recognition_event_id=event.id,
        payload_json=payload_json,
        signature=signature,
        status="pending",
        retry_count=0,
        next_retry_at=utcnow(),
    )
    db.add(outbox)
    db.commit()
    db.refresh(outbox)
    return outbox


def compute_next_retry(base_seconds: int, retry_count: int) -> datetime:
    return utcnow() + timedelta(seconds=base_seconds * (2 ** max(0, retry_count - 1)))


async def deliver_outbox_item(client: httpx.AsyncClient, outbox: WebhookOutbox, settings: AppSetting) -> tuple[bool, str | None]:
    if not settings.webhook_url:
        return False, "Webhook URL not configured"

    try:
        resp = await client.post(
            settings.webhook_url,
            content=outbox.payload_json,
            headers={
                "Content-Type": "application/json",
                "X-FaceApp-Signature": outbox.signature,
            },
            timeout=10.0,
        )
        if 200 <= resp.status_code < 300:
            return True, None
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)


def due_pending_items(db: Session) -> list[WebhookOutbox]:
    now = utcnow()
    stmt = (
        select(WebhookOutbox)
        .where(WebhookOutbox.status == "pending")
        .where(WebhookOutbox.next_retry_at <= now)
        .order_by(WebhookOutbox.next_retry_at.asc())
        .limit(50)
    )
    return list(db.execute(stmt).scalars().all())
