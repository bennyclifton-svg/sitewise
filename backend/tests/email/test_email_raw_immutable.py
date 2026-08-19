"""X1 Stage 15: raw project email is immutable; interpretation is the overlay."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, Insert as PGInsert
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from tests.conftest import run_async


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(_type, _compiler, **_kw):
    return "JSON"

PROJECT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SENT_AT = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)


def test_content_hash_agrees_across_providers() -> None:
    from app.email.service import email_content_hash

    graph = email_content_hash(
        internet_message_id="<msg-1@example.com>",
        from_address="qs@consultant.com",
        sent_at=SENT_AT,
        subject="Fee proposal",
        body_text="Please find attached.",
    )
    gmail = email_content_hash(
        internet_message_id="<msg-1@example.com>",
        from_address="qs@consultant.com",
        sent_at=SENT_AT,
        subject="Fee proposal",
        body_text="Please find attached.",
    )
    assert graph == gmail
    assert len(graph) == 64


def test_content_hash_uses_ingest_bytes_content_hash() -> None:
    from ingest.hashing import bytes_content_hash

    from app.email.service import email_content_hash

    canonical = "\n".join(
        [
            "<msg-1@example.com>",
            "qs@consultant.com",
            SENT_AT.isoformat(),
            "Fee proposal",
            "Please find attached.",
        ]
    )
    assert email_content_hash(
        internet_message_id="<msg-1@example.com>",
        from_address="qs@consultant.com",
        sent_at=SENT_AT,
        subject="Fee proposal",
        body_text="Please find attached.",
    ) == bytes_content_hash(canonical.encode("utf-8"))


def test_orm_update_of_raw_column_raises_from_any_caller() -> None:
    from app.email.models import ProjectEmail, RawEmailImmutable

    engine = create_engine("sqlite:///:memory:")
    ProjectEmail.__table__.create(engine)
    session = Session(engine)
    email = ProjectEmail(
        id=uuid.uuid4(),
        provider="fake",
        provider_message_id="msg-1",
        from_address="qs@consultant.com",
        to_addresses=["pm@owner.com"],
        cc_addresses=[],
        subject="Fee proposal",
        sent_at=SENT_AT,
        body_text="Please find attached.",
        headers={},
        content_hash="a" * 64,
        created_at=datetime.now(UTC),
    )
    session.add(email)
    session.commit()

    email.subject = "mutated"
    with pytest.raises(RawEmailImmutable):
        session.commit()
    session.rollback()
    session.refresh(email)
    assert email.subject == "Fee proposal"
    session.close()
    engine.dispose()


def test_updating_match_does_not_change_subject_or_body() -> None:
    from app.email.models import ProjectEmail
    from app.email.service import update_email_interpretation

    email = ProjectEmail(
        id=uuid.uuid4(),
        provider="fake",
        provider_message_id="msg-2",
        from_address="qs@consultant.com",
        to_addresses=["pm@owner.com"],
        cc_addresses=[],
        subject="Fee proposal",
        sent_at=SENT_AT,
        body_text="Please find attached.",
        headers={},
        content_hash="b" * 64,
        created_at=datetime.now(UTC),
    )
    session = _InterpretationSession(email)

    run_async(
        update_email_interpretation(
            session,
            email.id,
            project_id=PROJECT_ID,
            match_basis="user",
            match_reviewed_by_user_id=ACTOR_ID,
        )
    )

    assert email.subject == "Fee proposal"
    assert email.body_text == "Please find attached."
    assert session.interpretation.project_id == PROJECT_ID
    assert session.interpretation.match_basis == "user"


def test_service_refuses_raw_column_update() -> None:
    from app.email.models import RawEmailImmutable
    from app.email.service import update_email_interpretation

    email_id = uuid.uuid4()
    session = SimpleNamespace(get=AsyncMock())
    with pytest.raises(RawEmailImmutable):
        run_async(
            update_email_interpretation(
                session,
                email_id,
                subject="mutated",
            )
        )
    session.get.assert_not_called()


class _StubProvider:
    name = "fake"

    def __init__(self, messages) -> None:
        self._messages = messages

    async def list_messages(self, *, since):
        return self._messages


def test_duplicate_provider_message_id_is_idempotent() -> None:
    from app.email.schemas import RawProviderMessage
    from app.email.service import import_provider_messages

    message = RawProviderMessage(
        provider="fake",
        provider_message_id="dup-1",
        internet_message_id="<dup-1@example.com>",
        from_address="qs@consultant.com",
        to_addresses=["pm@owner.com"],
        subject="Fee proposal",
        sent_at=SENT_AT,
        body_text="Please find attached.",
    )
    provider = _StubProvider([message])
    session = _ImportSession()

    first = run_async(
        import_provider_messages(session, provider=provider, actor_id=None)
    )
    second = run_async(
        import_provider_messages(session, provider=provider, actor_id=None)
    )

    assert first == 1
    assert second == 0
    assert len(session.emails) == 1


class _InterpretationSession:
    def __init__(self, email) -> None:
        self.email = email
        self.interpretation = None

    async def get(self, model, ident):
        from app.email.models import ProjectEmail, ProjectEmailInterpretation

        if model is ProjectEmail and ident == self.email.id:
            return self.email
        if model is ProjectEmailInterpretation and ident == self.email.id:
            return self.interpretation
        return None

    def add(self, obj) -> None:
        self.interpretation = obj


class _ImportSession:
    def __init__(self) -> None:
        self.emails: dict[tuple[str, str], dict] = {}
        self.attachments: list[dict] = []

    async def execute(self, statement):
        if isinstance(statement, PGInsert):
            params = dict(statement.compile().params)
            table = statement.table.name
            if table == "project_emails":
                key = (params["provider"], params["provider_message_id"])
                if key in self.emails:
                    return SimpleNamespace(scalar_one_or_none=lambda: None)
                self.emails[key] = params
                return SimpleNamespace(scalar_one_or_none=lambda: params["id"])
            if table == "project_email_attachments":
                self.attachments.append(params)
                return SimpleNamespace(scalar_one_or_none=lambda: params.get("id"))
        from sqlalchemy.sql import Select

        if isinstance(statement, Select):
            params = dict(statement.compile().params)
            provider = params.get("provider_1") or params.get("provider")
            message_id = params.get("provider_message_id_1") or params.get(
                "provider_message_id"
            )
            row = self.emails.get((provider, message_id))
            email_id = None if row is None else row["id"]
            return SimpleNamespace(
                scalar_one=lambda: email_id,
                scalar_one_or_none=lambda: email_id,
            )
        return SimpleNamespace(scalar_one_or_none=lambda: None, all=lambda: [])
