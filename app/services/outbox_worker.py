from __future__ import annotations

import asyncio

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AppSetting, WebhookOutbox
from app.services.webhook import compute_next_retry, deliver_outbox_item, due_pending_items


class OutboxWorker:
    def __init__(self) -> None:
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._settings = get_settings()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run_loop(self) -> None:
        async with httpx.AsyncClient() as client:
            while not self._stop.is_set():
                await self._process_once(client)
                await asyncio.sleep(2)

    async def _process_once(self, client: httpx.AsyncClient) -> None:
        db = SessionLocal()
        try:
            app_settings = db.execute(
                select(AppSetting).where(AppSetting.singleton_key == "default")
            ).scalar_one_or_none()
            if not app_settings:
                return
            pending = due_pending_items(db)
            for item in pending:
                await self._deliver_item(db, client, item, app_settings)
            db.commit()
        finally:
            db.close()

    async def _deliver_item(
        self,
        db,
        client: httpx.AsyncClient,
        item: WebhookOutbox,
        app_settings: AppSetting,
    ) -> None:
        ok, error = await deliver_outbox_item(client, item, app_settings)
        if ok:
            item.status = "sent"
            item.last_error = None
            return

        item.retry_count += 1
        item.last_error = error
        if item.retry_count >= app_settings.webhook_max_retries:
            item.status = "failed"
        else:
            item.status = "pending"
            item.next_retry_at = compute_next_retry(self._settings.webhook_retry_base_seconds, item.retry_count)
