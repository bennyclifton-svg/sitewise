"""X1 Stage 22: PROJECTCODE@in.sitewise.au files through canonical intake."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
OTHER_USER = uuid.UUID("22222222-2222-2222-2222-222222222222")
SENT_AT = datetime(2026, 8, 19, 11, 0, tzinfo=UTC)
SECRET = "inbound-test-secret"
ALIAS = "kavanagh-residence@in.sitewise.au"


def _project(*, slug: str = "kavanagh-residence", owner: uuid.UUID = USER_ID) -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=owner,
        slug=slug,
        title="Kavanagh Residence",
        workspace_path="04-projects/kavanagh-residence",
        phase="procurement",
        status="active",
        project_metadata={},
    )


class _AliasSession:
    def __init__(self, projects: list[Project]) -> None:
        self.projects = projects

    async def execute(self, statement):
        del statement
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: list(self.projects))
        )


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _payload(**overrides) -> dict:
    body = {
        "from": "qs@consultant.com",
        "to": [ALIAS],
        "cc": [],
        "subject": "Drawing issue",
        "sent_at": SENT_AT.isoformat(),
        "body_text": "See attached.",
        "headers": {"message-id": "<inbound-1@consultant.com>"},
        "attachments": [],
    }
    body.update(overrides)
    return body


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "email_inbound_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "email_inbound_domain", "in.sitewise.au")

    session = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_known_slug_alias_resolves_project() -> None:
    from app.email.inbound import project_for_inbound_alias

    project = _project()
    found = run_async(
        project_for_inbound_alias(
            _AliasSession([project]),
            address=ALIAS,
        )
    )
    assert found is project


def test_unknown_alias_resolves_none() -> None:
    from app.email.inbound import project_code_from_alias, project_for_inbound_alias

    assert project_code_from_alias("nobody@in.sitewise.au") == "nobody"
    assert project_code_from_alias("kavanagh-residence@gmail.com") is None
    found = run_async(
        project_for_inbound_alias(
            _AliasSession([]),
            address="nobody@in.sitewise.au",
        )
    )
    assert found is None


def test_alias_is_case_insensitive() -> None:
    from app.email.inbound import project_code_from_alias, project_for_inbound_alias

    assert (
        project_code_from_alias("Kavanagh-Residence@IN.SITEWISE.AU")
        == "kavanagh-residence"
    )
    project = _project()
    found = run_async(
        project_for_inbound_alias(
            _AliasSession([project]),
            address="Kavanagh-Residence@IN.SITEWISE.AU",
        )
    )
    assert found is project


def test_duplicate_slug_resolves_none() -> None:
    from app.email.inbound import project_for_inbound_alias

    first = _project()
    second = Project(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        owner_user_id=OTHER_USER,
        slug="kavanagh-residence",
        title="Other Kavanagh",
        workspace_path="04-projects/other-kavanagh",
        phase="procurement",
        status="active",
        project_metadata={},
    )
    found = run_async(
        project_for_inbound_alias(
            _AliasSession([first, second]),
            address=ALIAS,
        )
    )
    assert found is None


def test_oversized_inbound_payload_is_rejected_before_parsing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "email_inbound_max_body_bytes", 100)
    body = b"x" * 200
    with patch("json.loads") as loads:
        response = client.post(
            "/internal/email/inbound",
            content=body,
            headers={
                "content-type": "application/json",
                "X-Sitewise-Inbound-Signature": _sign(body),
            },
        )
    assert response.status_code == 413
    loads.assert_not_called()


def test_signature_is_verified_against_raw_body_not_reserialised_json(
    client: TestClient,
) -> None:
    raw = (
        b'{ "from" : "qs@consultant.com", "to" : ["kavanagh-residence@in.sitewise.au"],'
        b' "cc" : [], "subject" : "Hi", "sent_at" : "2026-08-19T11:00:00+00:00",'
        b' "body_text" : "x", "headers" : {}, "attachments" : [] }'
    )
    parsed = json.loads(raw)
    assert json.dumps(parsed).encode("utf-8") != raw
    with patch(
        "app.api.inbound_email.ingest_inbound_payload",
        new=AsyncMock(return_value={"email_id": str(EMAIL_ID)}),
    ):
        response = client.post(
            "/internal/email/inbound",
            content=raw,
            headers={
                "content-type": "application/json",
                "X-Sitewise-Inbound-Signature": _sign(raw),
            },
        )
    assert response.status_code == 200


def test_inbound_without_secret_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "email_inbound_webhook_secret", None)
    raw = json.dumps(_payload()).encode("utf-8")
    response = client.post(
        "/internal/email/inbound",
        content=raw,
        headers={
            "content-type": "application/json",
            "X-Sitewise-Inbound-Signature": _sign(raw),
        },
    )
    assert response.status_code == 404


def test_inbound_bad_signature_returns_401(client: TestClient) -> None:
    raw = json.dumps(_payload()).encode("utf-8")
    response = client.post(
        "/internal/email/inbound",
        content=raw,
        headers={
            "content-type": "application/json",
            "X-Sitewise-Inbound-Signature": "deadbeef",
        },
    )
    assert response.status_code == 401


def test_inbound_alias_ingests_attachment_through_canonical_intake() -> None:
    from app.email.inbound import ingest_inbound_payload
    from app.email.project_matching import ProjectMatch

    pdf = b"%PDF-bytes"
    payload = _payload(
        attachments=[
            {
                "filename": "A-101.pdf",
                "content_base64": base64.b64encode(pdf).decode("ascii"),
            }
        ]
    )
    project = _project()
    ingest = AsyncMock()
    with (
        patch(
            "app.email.inbound.project_for_inbound_alias",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.email.service._insert_raw_email",
            new=AsyncMock(return_value=EMAIL_ID),
        ),
        patch("app.email.service._insert_attachment_refs", new=AsyncMock()),
        patch("app.email.service._insert_interpretation", new=AsyncMock()) as insert_interp,
        patch("app.email.service._emit_email_project_verbs", new=AsyncMock()),
        patch("app.email.service.ingest_email_attachment", new=ingest),
        patch("app.email.attachments.classify", create=True) as classify,
    ):
        result = run_async(ingest_inbound_payload(AsyncMock(), payload))
    assert result["email_id"] == str(EMAIL_ID)
    match = insert_interp.call_args.args[2]
    assert isinstance(match, ProjectMatch)
    assert match.project_id == PROJECT_ID
    assert match.basis == "alias"
    assert match.confidence == 1.0
    ingest.assert_called_once()
    assert ingest.call_args.kwargs["filename"] == "A-101.pdf"
    assert ingest.call_args.kwargs["content"] == pdf
    assert ingest.call_args.kwargs["created_by_user_id"] == USER_ID
    classify.assert_not_called()


def test_inbound_does_not_send_mail() -> None:
    from app.email.inbound import ingest_inbound_payload

    send = AsyncMock()
    with (
        patch(
            "app.email.inbound.project_for_inbound_alias",
            new=AsyncMock(return_value=_project()),
        ),
        patch(
            "app.email.service._insert_raw_email",
            new=AsyncMock(return_value=EMAIL_ID),
        ),
        patch("app.email.service._insert_attachment_refs", new=AsyncMock()),
        patch("app.email.service._insert_interpretation", new=AsyncMock()),
        patch("app.email.service._emit_email_project_verbs", new=AsyncMock()),
        patch("app.email.service.ingest_email_attachment", new=AsyncMock()),
        patch("app.email.service.send_email_draft", new=send),
        patch("app.email.inbound.send_email_draft", new=send, create=True),
    ):
        run_async(ingest_inbound_payload(AsyncMock(), _payload()))
    send.assert_not_called()


def test_inbound_rejects_the_same_filenames_inbox_rejects() -> None:
    from app.email.inbound import ingest_inbound_payload
    from app.inbox.service import (
        InboxUploadItem,
        InboxUploadValidationError,
        validate_upload_item,
    )

    with pytest.raises(InboxUploadValidationError):
        validate_upload_item(InboxUploadItem(filename="malware.exe", content=b"MZ"))

    ingest = AsyncMock()
    payload = _payload(
        attachments=[
            {
                "filename": "malware.exe",
                "content_base64": base64.b64encode(b"MZ").decode("ascii"),
            }
        ]
    )
    with (
        patch(
            "app.email.inbound.project_for_inbound_alias",
            new=AsyncMock(return_value=_project()),
        ),
        patch("app.email.service.ingest_email_attachment", new=ingest),
    ):
        with pytest.raises(InboxUploadValidationError):
            run_async(ingest_inbound_payload(AsyncMock(), payload))
    ingest.assert_not_called()
