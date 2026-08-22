"""X1 Stage 19: drafts persist without sending; send requires an actor."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest

from app.database.project import Project
from app.email.providers.fake import FakeProvider
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _project(*, owner: uuid.UUID = USER_ID, project_id: uuid.UUID = PROJECT_ID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=owner,
        slug="kavanagh-residence",
        title="Kavanagh Residence",
        workspace_path="04-projects/kavanagh-residence",
        phase="procurement",
        status="active",
        project_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


class _DraftSession:
    def __init__(
        self,
        *,
        project: Project,
        draft=None,
        lock: asyncio.Lock | None = None,
    ) -> None:
        self.project = project
        self.draft = draft
        self.added: list[object] = []
        self.commits = 0
        self._lock = lock or asyncio.Lock()
        self._held = False

    async def get(self, model, ident, with_for_update: bool = False):
        from app.email.models import ProjectEmailDraft

        if with_for_update:
            await self._lock.acquire()
            self._held = True
        if model is Project and ident == self.project.id:
            return self.project
        if model is ProjectEmailDraft and self.draft is not None and ident == self.draft.id:
            return self.draft
        return None

    def add(self, obj) -> None:
        self.added.append(obj)
        self.draft = obj

    async def flush(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None

    async def rollback(self) -> None:
        if self._held:
            self._lock.release()
            self._held = False

    async def commit(self) -> None:
        self.commits += 1
        if self._held:
            self._lock.release()
            self._held = False


def test_create_draft_does_not_send() -> None:
    from app.email.service import create_email_draft

    provider = FakeProvider()
    session = _DraftSession(project=_project())
    draft = run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    assert draft.status == "draft"
    assert draft.provider_draft_id is not None
    assert provider.sent == []
    assert draft.sent_at is None
    assert draft.provider_message_id is None


def test_send_without_actor_raises() -> None:
    from app.email.service import create_email_draft, send_email_draft

    provider = FakeProvider()
    session = _DraftSession(project=_project())
    draft = run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    with pytest.raises(ValueError, match="actor_id"):
        run_async(
            send_email_draft(
                session,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=None,
                provider=provider,
            )
        )
    assert provider.sent == []
    assert draft.status == "draft"


def test_concurrent_send_of_one_draft_sends_once() -> None:
    from app.email.service import EmailDraftConflict, create_email_draft, send_email_draft

    class _GateProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.proceed = asyncio.Event()

        async def send_draft(
            self,
            provider_draft_id: str,
            *,
            actor_id: uuid.UUID | None,
            draft=None,
        ):
            self.started.set()
            await self.proceed.wait()
            return await super().send_draft(
                provider_draft_id, actor_id=actor_id, draft=draft
            )

    provider = _GateProvider()
    lock = asyncio.Lock()
    first = _DraftSession(project=_project(), lock=lock)
    draft = run_async(
        create_email_draft(
            first,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    second = _DraftSession(project=first.project, draft=draft, lock=lock)

    async def _race() -> None:
        task = asyncio.create_task(
            send_email_draft(
                first,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                provider=provider,
            )
        )
        await provider.started.wait()
        with pytest.raises(EmailDraftConflict):
            await send_email_draft(
                second,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                provider=provider,
            )
        provider.proceed.set()
        sent = await task
        assert sent.status == "sent"

    run_async(_race())
    assert len(provider.sent) == 1
    assert draft.status == "sent"


def test_provider_failure_leaves_send_failed_not_draft() -> None:
    from app.email.service import create_email_draft, send_email_draft

    class _BoomProvider(FakeProvider):
        async def send_draft(
            self,
            provider_draft_id: str,
            *,
            actor_id: uuid.UUID | None,
            draft=None,
        ):
            raise RuntimeError("mailbox unavailable")

    provider = _BoomProvider()
    session = _DraftSession(project=_project())
    draft = run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    with pytest.raises(RuntimeError, match="mailbox unavailable"):
        run_async(
            send_email_draft(
                session,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                provider=provider,
            )
        )
    assert draft.status == "send_failed"
    assert draft.send_error is not None
    assert "mailbox" in draft.send_error
    assert provider.sent == []


def test_send_failed_draft_cannot_be_silently_resent() -> None:
    from app.email.service import EmailDraftConflict, create_email_draft, send_email_draft

    class _BoomProvider(FakeProvider):
        async def send_draft(
            self,
            provider_draft_id: str,
            *,
            actor_id: uuid.UUID | None,
            draft=None,
        ):
            raise RuntimeError("mailbox unavailable")

    provider = _BoomProvider()
    session = _DraftSession(project=_project())
    draft = run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    with pytest.raises(RuntimeError):
        run_async(
            send_email_draft(
                session,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                provider=provider,
            )
        )
    with pytest.raises(EmailDraftConflict, match="send_failed"):
        run_async(
            send_email_draft(
                session,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                provider=FakeProvider(),
            )
        )
    assert draft.status == "send_failed"


def test_send_requires_project_owner() -> None:
    from app.email.service import create_email_draft, send_email_draft
    from app.email.service import EmailNotFound

    provider = FakeProvider()
    session = _DraftSession(project=_project())
    draft = run_async(
        create_email_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            subject="Re: Fee proposal",
            body_text="Thanks.",
            provider=provider,
        )
    )
    with pytest.raises(EmailNotFound):
        run_async(
            send_email_draft(
                session,
                project_id=PROJECT_ID,
                draft_id=draft.id,
                actor_id=OTHER_USER,
                provider=provider,
            )
        )
    assert provider.sent == []
    assert draft.status == "draft"
