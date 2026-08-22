"""A sent draft must leave as the project, carrying its thread with it."""

from __future__ import annotations

import uuid

import pytest

from app.config import settings
from app.email.schemas import ProviderDraft
from tests.conftest import run_async
from tests.email.test_email_drafts import PROJECT_ID, USER_ID, _DraftSession, _project


class _RecordingProvider:
    """Stands in for Mailgun: records what it was actually handed to send."""

    name = "mailgun"

    def __init__(self) -> None:
        self.sent: list[ProviderDraft | None] = []

    async def create_draft(self, draft: ProviderDraft) -> str:
        return "mailgun-1"

    async def send_draft(
        self,
        provider_draft_id: str,
        *,
        actor_id: uuid.UUID | None,
        draft: ProviderDraft | None = None,
    ) -> str:
        self.sent.append(draft)
        return "<sent@sitewise.au>"


def _make_draft(provider: _RecordingProvider, session: _DraftSession, **kwargs):
    from app.email.service import create_email_draft

    return run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
            **kwargs,
        )
    )


def test_send_hands_the_provider_the_draft_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mailgun holds no draft, so the content has to travel with the send."""
    from app.email.service import send_email_draft

    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    provider = _RecordingProvider()
    session = _DraftSession(project=_project())
    draft = _make_draft(provider, session)

    run_async(
        send_email_draft(
            session,
            project_id=PROJECT_ID,
            draft_id=draft.id,
            actor_id=USER_ID,
            provider=provider,
        )
    )

    sent = provider.sent[0]
    assert sent is not None
    assert sent.to_addresses == ["qs@consultant.com"]
    assert sent.subject == "Re: Fee proposal"
    assert sent.body_text == "Thanks."


def test_send_uses_the_project_alias_as_the_from_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without this the reply lands in a personal mailbox, not the project."""
    from app.email.service import send_email_draft

    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    provider = _RecordingProvider()
    session = _DraftSession(project=_project())
    draft = _make_draft(provider, session)

    run_async(
        send_email_draft(
            session,
            project_id=PROJECT_ID,
            draft_id=draft.id,
            actor_id=USER_ID,
            provider=provider,
        )
    )

    assert provider.sent[0].from_address == "kavanagh-residence@sitewise.au"


def test_a_successful_send_records_the_provider_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.email.service import send_email_draft

    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    provider = _RecordingProvider()
    session = _DraftSession(project=_project())
    draft = _make_draft(provider, session)

    sent = run_async(
        send_email_draft(
            session,
            project_id=PROJECT_ID,
            draft_id=draft.id,
            actor_id=USER_ID,
            provider=provider,
        )
    )

    assert sent.status == "sent"
    assert sent.provider_message_id == "<sent@sitewise.au>"
