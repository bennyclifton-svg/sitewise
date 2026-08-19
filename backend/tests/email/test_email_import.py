"""X1 Stage 15: import raw email and attachment refs without ingesting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.dialects.postgresql import Insert as PGInsert
from sqlalchemy.sql import Select

from tests.conftest import run_async

SENT_AT = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)


class _ImportSession:
    def __init__(self) -> None:
        self.emails: dict[tuple[str, str], dict] = {}
        self.emails_by_id: dict[uuid.UUID, dict] = {}
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
                self.emails_by_id[params["id"]] = params
                return SimpleNamespace(scalar_one_or_none=lambda: params["id"])
            if table == "project_email_attachments":
                self.attachments.append(params)
                return SimpleNamespace(scalar_one_or_none=lambda: params.get("id"))
        if isinstance(statement, Select):
            params = dict(statement.compile().params)
            provider = params.get("provider_1") or params.get("provider")
            message_id = params.get("provider_message_id_1") or params.get(
                "provider_message_id"
            )
            row = self.emails.get((provider, message_id))
            if row is None:
                return SimpleNamespace(
                    scalar_one=lambda: (_ for _ in ()).throw(LookupError()),
                    scalar_one_or_none=lambda: None,
                )
            return SimpleNamespace(
                scalar_one=lambda: row["id"],
                scalar_one_or_none=lambda: row["id"],
            )
        return SimpleNamespace(scalar_one_or_none=lambda: None)


def test_import_does_not_call_ingest_hosted_file() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderAttachment, RawProviderMessage
    from app.email.service import import_provider_messages

    provider = FakeProvider()
    provider.add_message(
        RawProviderMessage(
            provider="fake",
            provider_message_id="msg-att",
            from_address="qs@consultant.com",
            to_addresses=["pm@owner.com"],
            subject="Invoice",
            sent_at=SENT_AT,
            body_text="See attached.",
            attachments=[
                RawProviderAttachment(
                    provider_attachment_id="att-1",
                    filename="invoice.pdf",
                    content_type="application/pdf",
                    size_bytes=2048,
                )
            ],
        ),
        attachment_bytes={"att-1": b"%PDF-bytes"},
    )
    session = _ImportSession()

    with (
        patch("ingest.hosted.ingest_hosted_file") as ingest,
        patch("ingest.classify.classify_entry") as classify,
    ):
        count = run_async(
            import_provider_messages(session, provider=provider, actor_id=None)
        )

    assert count == 1
    ingest.assert_not_called()
    classify.assert_not_called()
    assert session.attachments
    assert all(row.get("content_hash") is None for row in session.attachments)
    assert all(row.get("source_document_id") is None for row in session.attachments)
    still_on_provider = run_async(
        provider.get_attachment_bytes("msg-att", "att-1")
    )
    assert still_on_provider == b"%PDF-bytes"


def test_import_stores_attachment_refs_without_bytes() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderAttachment, RawProviderMessage
    from app.email.service import import_provider_messages

    provider = FakeProvider()
    provider.add_message(
        RawProviderMessage(
            provider="fake",
            provider_message_id="msg-refs",
            from_address="qs@consultant.com",
            to_addresses=["pm@owner.com"],
            subject="Drawings",
            sent_at=SENT_AT,
            body_text="IFC attached.",
            attachments=[
                RawProviderAttachment(
                    provider_attachment_id="att-s203",
                    filename="S203.pdf",
                    content_type="application/pdf",
                    size_bytes=4096,
                )
            ],
        )
    )
    session = _ImportSession()
    run_async(import_provider_messages(session, provider=provider, actor_id=None))

    assert len(session.attachments) == 1
    ref = session.attachments[0]
    assert ref["filename"] == "S203.pdf"
    assert ref["provider_attachment_id"] == "att-s203"
    assert ref["content_hash"] is None
    assert ref["source_document_id"] is None


def test_missing_sent_at_does_not_discard_message() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderMessage
    from app.email.service import import_provider_messages

    provider = FakeProvider()
    provider.add_message(
        RawProviderMessage(
            provider="fake",
            provider_message_id="msg-nodate",
            from_address="qs@consultant.com",
            to_addresses=["pm@owner.com"],
            subject="No Date header",
            sent_at=None,
            body_text="Still evidence.",
            headers={"Date": "not a date"},
        )
    )
    session = _ImportSession()
    count = run_async(
        import_provider_messages(session, provider=provider, actor_id=None)
    )
    assert count == 1
    row = next(iter(session.emails.values()))
    assert row["sent_at"] is None
    assert row["headers"]["Date"] == "not a date"
    assert row["body_text"] == "Still evidence."
