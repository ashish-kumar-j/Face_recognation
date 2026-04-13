from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "operator"] = "operator"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str


class PersonCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    external_id: str | None = Field(default=None, max_length=120)


class PersonResponse(BaseModel):
    id: int
    display_name: str
    external_id: str | None
    active: bool


class CameraEnrollmentRequest(BaseModel):
    frame_base64: str


class RecognitionFrameRequest(BaseModel):
    frame_base64: str


class EventResponse(BaseModel):
    id: int
    match_status: str
    score: float | None
    liveness_score: float | None
    person_id: int | None
    snapshot_path: str | None
    created_at: datetime


class WebhookSettingsRequest(BaseModel):
    webhook_url: str | None = None
    webhook_secret: str | None = None
    strict_match_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    store_unknown_snapshots: bool | None = None
    store_known_snapshots: bool | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class SettingsResponse(BaseModel):
    strict_match_threshold: float
    store_unknown_snapshots: bool
    store_known_snapshots: bool
    webhook_url: str | None
    webhook_max_retries: int
    retention_days: int


class WebhookOutboxResponse(BaseModel):
    id: int
    recognition_event_id: int
    status: str
    retry_count: int
    next_retry_at: datetime
    last_error: str | None
    created_at: datetime


class RecognitionResult(BaseModel):
    match_status: Literal["known", "unknown", "rejected_liveness"]
    person_id: int | None = None
    person_name: str | None = None
    score: float | None = None
    liveness_score: float | None = None
    threshold: float
    message: str
