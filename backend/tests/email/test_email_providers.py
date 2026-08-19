"""X1 Stage 15: provider-neutral email interface; no live Graph/Gmail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from tests.conftest import run_async

SENT_AT = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
ACTOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def test_fake_provider_round_trips_a_message() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderAttachment, RawProviderMessage

    provider = FakeProvider()
    message = RawProviderMessage(
        provider="fake",
        provider_message_id="msg-roundtrip",
        provider_thread_id="thread-1",
        internet_message_id="<roundtrip@example.com>",
        from_address="qs@consultant.com",
        to_addresses=["pm@owner.com"],
        subject="Fee proposal",
        sent_at=SENT_AT,
        body_text="Please find attached.",
        attachments=[
            RawProviderAttachment(
                provider_attachment_id="att-1",
                filename="fee.pdf",
                content_type="application/pdf",
                size_bytes=12,
            )
        ],
    )
    provider.add_message(message, attachment_bytes={"att-1": b"%PDF-fake"})

    listed = run_async(provider.list_messages(since=None))
    assert len(listed) == 1
    assert listed[0].provider_message_id == "msg-roundtrip"
    fetched = run_async(provider.get_message("msg-roundtrip"))
    assert fetched.subject == "Fee proposal"
    assert fetched.body_text == "Please find attached."
    payload = run_async(provider.get_attachment_bytes("msg-roundtrip", "att-1"))
    assert payload == b"%PDF-fake"


def test_graph_provider_is_not_callable_yet() -> None:
    from app.email.providers.base import ProviderNotConfigured
    from app.email.providers.microsoft_graph import MicrosoftGraphProvider

    provider = MicrosoftGraphProvider()
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.list_messages(since=None))
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.get_message("any"))
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.get_attachment_bytes("any", "att"))
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.create_draft(_draft()))
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.send_draft("draft-1", actor_id=ACTOR_ID))


def test_gmail_provider_is_not_callable_yet() -> None:
    from app.email.providers.base import ProviderNotConfigured
    from app.email.providers.gmail import GmailProvider

    provider = GmailProvider()
    with pytest.raises(ProviderNotConfigured):
        run_async(provider.list_messages(since=None))


def test_default_provider_is_fake() -> None:
    from app.config import settings
    from app.email.providers import email_provider_from_settings

    assert settings.email_provider == "fake"
    provider = email_provider_from_settings(settings)
    assert provider.name == "fake"


def test_graph_without_secrets_raises_not_configured() -> None:
    from types import SimpleNamespace

    from app.email.providers import email_provider_from_settings
    from app.email.providers.base import ProviderNotConfigured

    graph_settings = SimpleNamespace(
        email_provider="microsoft_graph",
        microsoft_graph_tenant_id=None,
        microsoft_graph_client_id=None,
        microsoft_graph_client_secret=None,
        microsoft_graph_refresh_token=None,
        microsoft_graph_mailbox_user=None,
        gmail_client_id=None,
        gmail_client_secret=None,
        gmail_refresh_token=None,
    )
    with pytest.raises(ProviderNotConfigured):
        email_provider_from_settings(graph_settings)


def test_send_draft_without_actor_raises() -> None:
    from app.email.providers.fake import FakeProvider

    provider = FakeProvider()
    draft_id = run_async(provider.create_draft(_draft()))
    with pytest.raises(ValueError, match="actor_id"):
        run_async(provider.send_draft(draft_id, actor_id=None))
    run_async(provider.send_draft(draft_id, actor_id=ACTOR_ID))
    assert provider.sent == [(draft_id, ACTOR_ID)]


def _draft():
    from app.email.schemas import ProviderDraft

    return ProviderDraft(
        to_addresses=["qs@consultant.com"],
        subject="Re: Fee proposal",
        body_text="Thanks.",
    )
