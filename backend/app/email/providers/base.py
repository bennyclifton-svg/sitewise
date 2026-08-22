from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.email.schemas import ProviderDraft, RawProviderMessage


class ProviderNotConfigured(RuntimeError):
    """Live Graph/Gmail adapters are stubs until secrets exist (OD-14)."""


class EmailProvider(Protocol):
    name: str

    async def list_messages(
        self, *, since: datetime | None
    ) -> list[RawProviderMessage]: ...

    async def get_message(self, provider_message_id: str) -> RawProviderMessage: ...

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes: ...

    async def create_draft(self, draft: ProviderDraft) -> str: ...

    async def send_draft(
        self,
        provider_draft_id: str,
        *,
        actor_id: uuid.UUID | None,
        draft: ProviderDraft | None = None,
    ) -> str | None:
        """Send a previously created draft.

        `draft` carries the content for providers that hold no server-side
        draft of their own (Mailgun). Providers that do — Gmail, Graph — ignore
        it and send the copy they already have.
        """
        ...
