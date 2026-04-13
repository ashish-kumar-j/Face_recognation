from __future__ import annotations

import base64
import uuid
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings


settings = get_settings()


def ensure_data_dirs() -> None:
    Path(settings.sample_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.snapshot_dir).mkdir(parents=True, exist_ok=True)


def decode_base64_image(frame_base64: str) -> np.ndarray:
    payload = frame_base64.split(",", 1)[-1]
    raw = base64.b64decode(payload)
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image payload")
    return image


def save_image(image: np.ndarray, category: str) -> str:
    ensure_data_dirs()
    directory = Path(settings.sample_dir if category == "sample" else settings.snapshot_dir)
    file_path = directory / f"{uuid.uuid4().hex}.jpg"
    cv2.imwrite(str(file_path), image)
    return str(file_path)
