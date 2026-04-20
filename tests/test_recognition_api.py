from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from app.schemas import RecognitionResult


def _image_data_url() -> str:
    arr = np.zeros((16, 16, 3), dtype=np.uint8)
    arr[:, :, 0] = 120
    arr[:, :, 1] = 80
    arr[:, :, 2] = 20
    image = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def test_identify_endpoint_returns_result(client, monkeypatch):
    reg = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123", "role": "admin"},
    )
    assert reg.status_code == 200

    from app.api import recognition as recognition_api

    def fake_recognize_frame(db, image, session_key):
        return RecognitionResult(
            match_status="known",
            person_id=1,
            person_name="Alice",
            score=0.95,
            liveness_score=0.88,
            threshold=0.82,
            message="Known face identified",
        )

    monkeypatch.setattr(recognition_api.recognition_service, "recognize_frame", fake_recognize_frame)

    resp = client.post("/api/recognition/identify", json={"frame_base64": _image_data_url()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["match_status"] == "known"
    assert body["person_name"] == "Alice"


def test_identify_endpoint_rejects_invalid_payload(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123", "role": "admin"},
    )
    assert reg.status_code == 200

    resp = client.post("/api/recognition/identify", json={"frame_base64": "not-a-valid-image"})
    assert resp.status_code == 400
    assert "Invalid image payload" in resp.json()["detail"]
