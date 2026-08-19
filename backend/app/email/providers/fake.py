from __future__ import annotations

import uuid
from datetime import datetime

from app.email.schemas import ProviderDraft, RawProviderMessage


class FakeProvider:
    """In-memory provider used by every email test through Stage 19."""

    name = "fake"

    def __init__(self) -> None:
        self._messages: dict[str, RawProviderMessage] = {}
        self._attachment_bytes: dict[tuple[str, str], bytes] = {}
        self._drafts: dict[str, ProviderDraft] = {}
        self.sent: list[tuple[str, uuid.UUID]] = []

    def add_message(
        self,
        message: RawProviderMessage,
        *,
        attachment_bytes: dict[str, bytes] | None = None,
    ) -> None:
        self._messages[message.provider_message_id] = message
        for attachment_id, payload in (attachment_bytes or {}).items():
            self._attachment_bytes[(message.provider_message_id, attachment_id)] = (
                payload
            )

    async def list_messages(
        self, *, since: datetime | None
    ) -> list[RawProviderMessage]:
        messages = list(self._messages.values())
        if since is None:
            return messages
        return [
            message
            for message in messages
            if message.sent_at is None or message.sent_at >= since
        ]

    async def get_message(self, provider_message_id: str) -> RawProviderMessage:
        try:
            return self._messages[provider_message_id]
        except KeyError as exc:
            raise KeyError(provider_message_id) from exc

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes:
        try:
            return self._attachment_bytes[(provider_message_id, attachment_id)]
        except KeyError as exc:
            raise KeyError((provider_message_id, attachment_id)) from exc

    async def create_draft(self, draft: ProviderDraft) -> str:
        draft_id = f"draft-{len(self._drafts) + 1}"
        self._drafts[draft_id] = draft
        return draft_id

    async def send_draft(
        self, provider_draft_id: str, *, actor_id: uuid.UUID | None
    ) -> None:
        if actor_id is None:
            raise ValueError("actor_id is required to send a draft")
        if provider_draft_id not in self._drafts:
            raise KeyError(provider_draft_id)
        self.sent.append((provider_draft_id, actor_id))
        return f"sent-{provider_draft_id}"
