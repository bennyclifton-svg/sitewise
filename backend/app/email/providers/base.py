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
        self, provider_draft_id: str, *, actor_id: uuid.UUID | None
    ) -> str | None: ...
