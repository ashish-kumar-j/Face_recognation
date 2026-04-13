from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine
from app.models import AppSetting
from app.services.storage import ensure_data_dirs


def init_app_state() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_data_dirs()

    settings = get_settings()
    db = Session(bind=engine)
    try:
        existing = db.execute(select(AppSetting).where(AppSetting.singleton_key == "default")).scalar_one_or_none()
        if not existing:
            db.add(
                AppSetting(
                    singleton_key="default",
                    strict_match_threshold=settings.strict_match_threshold,
                    store_unknown_snapshots=False,
                    store_known_snapshots=False,
                    webhook_max_retries=settings.webhook_max_retries,
                    retention_days=30,
                )
            )
            db.commit()
    finally:
        db.close()
