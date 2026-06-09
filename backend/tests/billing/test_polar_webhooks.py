import base64
import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers

from app.billing.webhooks import parse_polar_payload, verify_polar_webhook
from app.config import settings


def _signed_headers(payload: bytes, secret: str) -> Headers:
    webhook_id = "evt_test"
    timestamp = str(int(time.time()))
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{webhook_id}.{timestamp}.".encode() + payload
    signature = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
    return Headers(
        {
            "webhook-id": webhook_id,
            "webhook-timestamp": timestamp,
            "webhook-signature": f"v1,{signature}",
        }
    )


def test_verify_polar_webhook_accepts_standard_webhook_signature(monkeypatch):
    secret = "whsec_" + base64.b64encode(b"test-secret").decode()
    payload = b'{"type":"customer.created","data":{"id":"cus_1"}}'
    monkeypatch.setattr(settings, "polar_webhook_secret", secret)

    verify_polar_webhook(_signed_headers(payload, secret), payload)


def test_verify_polar_webhook_rejects_tampered_payload(monkeypatch):
    secret = "whsec_" + base64.b64encode(b"test-secret").decode()
    payload = b'{"type":"customer.created","data":{"id":"cus_1"}}'
    monkeypatch.setattr(settings, "polar_webhook_secret", secret)

    with pytest.raises(HTTPException):
        verify_polar_webhook(_signed_headers(payload, secret), b'{"type":"customer.updated"}')


def test_parse_polar_payload_requires_json_object():
    assert parse_polar_payload(b'{"type":"customer.created","data":{}}')["type"] == "customer.created"

    with pytest.raises(HTTPException):
        parse_polar_payload(b"[]")
