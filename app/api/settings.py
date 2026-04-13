from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import enforce_csrf, require_admin
from app.models import AppSetting, User
from app.schemas import SettingsResponse, WebhookSettingsRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.put("/webhook", response_model=SettingsResponse)
def update_webhook_settings(
    payload: WebhookSettingsRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    __: None = Depends(enforce_csrf),
):
    settings = db.execute(select(AppSetting).where(AppSetting.singleton_key == "default")).scalar_one()

    for key in [
        "webhook_url",
        "webhook_secret",
        "strict_match_threshold",
        "store_unknown_snapshots",
        "store_known_snapshots",
        "retention_days",
    ]:
        value = getattr(payload, key)
        if value is not None:
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return SettingsResponse(
        strict_match_threshold=settings.strict_match_threshold,
        store_unknown_snapshots=settings.store_unknown_snapshots,
        store_known_snapshots=settings.store_known_snapshots,
        webhook_url=settings.webhook_url,
        webhook_max_retries=settings.webhook_max_retries,
        retention_days=settings.retention_days,
    )
