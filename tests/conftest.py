from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("FACE_APP_DATABASE_URL", "sqlite:///./test_face_app.db")
os.environ.setdefault("FACE_APP_SECRET_KEY", "test-secret")

from app.bootstrap import init_app_state
from app.db import Base, SessionLocal, engine
from app.models import AppSetting
from app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            AppSetting(
                singleton_key="default",
                strict_match_threshold=0.82,
                store_unknown_snapshots=False,
                store_known_snapshots=False,
                webhook_max_retries=5,
                retention_days=30,
            )
        )
        db.commit()
    finally:
        db.close()

    yield


@pytest.fixture
def client():
    init_app_state()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def cleanup_db_file():
    yield
    db_file = Path("test_face_app.db")
    if db_file.exists():
        db_file.unlink()
