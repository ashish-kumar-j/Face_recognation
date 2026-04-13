from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth, pages, persons, recognition, settings, webhook
from app.bootstrap import init_app_state
from app.config import get_settings
from app.services.outbox_worker import OutboxWorker

config = get_settings()
worker = OutboxWorker()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_app_state()
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title=config.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(recognition.router)
app.include_router(settings.router)
app.include_router(webhook.router)


@app.get("/health")
def health():
    return {"ok": True}
