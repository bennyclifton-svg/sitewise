"""Mailgun inbound adapter files through the Stage 22 alias ingest path."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.session import get_db
from app.email.mailgun import inbound_payload_from_mailgun, mailgun_signature_valid
from app.main import fastapi_app as app

EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SIGNING_KEY = "mailgun-test-signing-key"
ALIAS = "kavanagh-residence@sitewise.au"


def _sign(timestamp: str, token: str, key: str = SIGNING_KEY) -> str:
    return hmac.new(
        key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "mailgun_inbound_signing_key", SIGNING_KEY)
    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")

    session = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_mailgun_signature_matches_timestamp_and_token() -> None:
    timestamp = "1770000000"
    token = "route-token"
    assert mailgun_signature_valid(
        signing_key=SIGNING_KEY,
        timestamp=timestamp,
        token=token,
        signature=_sign(timestamp, token),
    )
    assert not mailgun_signature_valid(
        signing_key=SIGNING_KEY,
        timestamp=timestamp,
        token=token,
        signature="deadbeef",
    )


def test_mailgun_maps_recipient_and_attachment() -> None:
    pdf = b"%PDF-bytes"
    payload = inbound_payload_from_mailgun(
        fields={
            "from": "QS <qs@consultant.com>",
            "recipient": ALIAS,
            "To": f"SiteWise <{ALIAS}>",
            "Cc": "owner@example.com",
            "subject": "Drawing issue",
            "body-plain": "See attached.",
            "timestamp": "1770000000",
            "Message-Id": "<inbound-1@consultant.com>",
        },
        attachments=[("A-101.pdf", pdf, "application/pdf")],
    )
    assert payload["from"] == "qs@consultant.com"
    assert payload["to"] == [ALIAS]
    assert payload["cc"] == ["owner@example.com"]
    assert payload["headers"]["message-id"] == "<inbound-1@consultant.com>"
    assert payload["attachments"][0]["filename"] == "A-101.pdf"


def test_mailgun_without_signing_key_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "mailgun_inbound_signing_key", None)
    response = client.post("/internal/email/inbound/mailgun", data={"from": "a@b.com"})
    assert response.status_code == 404


def test_mailgun_bad_signature_returns_401(client: TestClient) -> None:
    timestamp = str(int(time.time()))
    response = client.post(
        "/internal/email/inbound/mailgun",
        data={
            "from": "qs@consultant.com",
            "recipient": ALIAS,
            "timestamp": timestamp,
            "token": "route-token",
            "signature": "deadbeef",
        },
    )
    assert response.status_code == 401


def test_mailgun_stale_timestamp_returns_401(client: TestClient) -> None:
    timestamp = str(int(time.time()) - 3600)
    token = "route-token"
    response = client.post(
        "/internal/email/inbound/mailgun",
        data={
            "from": "qs@consultant.com",
            "recipient": ALIAS,
            "timestamp": timestamp,
            "token": token,
            "signature": _sign(timestamp, token),
        },
    )
    assert response.status_code == 401


def test_mailgun_inbound_ingests_through_canonical_path(client: TestClient) -> None:
    timestamp = str(int(time.time()))
    token = "route-token"
    with patch(
        "app.api.inbound_email.ingest_inbound_payload",
        new=AsyncMock(return_value={"email_id": str(EMAIL_ID)}),
    ) as ingest:
        response = client.post(
            "/internal/email/inbound/mailgun",
            data={
                "from": "qs@consultant.com",
                "recipient": ALIAS,
                "To": ALIAS,
                "subject": "Drawing issue",
                "body-plain": "See attached.",
                "timestamp": timestamp,
                "token": token,
                "signature": _sign(timestamp, token),
                "Message-Id": "<inbound-1@consultant.com>",
            },
            files={"attachment-1": ("A-101.pdf", b"%PDF-bytes", "application/pdf")},
        )
    assert response.status_code == 200
    assert response.json() == {"email_id": str(EMAIL_ID)}
    payload = ingest.call_args.args[1]
    assert payload["to"] == [ALIAS]
    assert payload["attachments"][0]["filename"] == "A-101.pdf"
