from __future__ import annotations

from datetime import datetime, timezone

from app.services.webhook import compute_next_retry, sign_payload


def test_sign_payload_uses_sha256_prefix():
    sig = sign_payload('{"hello":"world"}', "secret")
    assert sig.startswith("sha256=")
    assert len(sig) > 20


def test_compute_next_retry_increases_with_retry_count():
    one = compute_next_retry(10, 1)
    three = compute_next_retry(10, 3)
    assert three > one
    assert isinstance(one, datetime)
    assert one.tzinfo == timezone.utc
