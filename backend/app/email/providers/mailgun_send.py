"""Send project mail through Mailgun, from the project's own alias.

Mailgun already owns the inbound side of `sitewise.au` (MX, SPF, DKIM), so
sending through it lets a message leave as `{slug}@sitewise.au` and a reply
come straight back down the inbound route into the same project. Gmail and
Graph cannot do that — they always send as the connected mailbox.

Mailgun has no server-side draft concept. `create_draft` therefore mints a
local id and stores nothing; the canonical draft is the `project_email_drafts`
row, and `send_draft` must be handed that content to send.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import httpx

from app.email.providers.base import ProviderNotConfigured
from app.email.schemas import ProviderDraft, RawProviderMessage

DEFAULT_API_BASE = "https://api.mailgun.net"
SEND_TIMEOUT_SECONDS = 30.0


class MailgunProvider:
    name = "mailgun"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        sending_domain: str | None = None,
        api_base: str | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key or ""
        self._sending_domain = (sending_domain or "").strip().lower()
        self._api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self._http = http

    @classmethod
    def from_settings(cls, settings) -> "MailgunProvider":
        return cls(
            api_key=getattr(settings, "mailgun_api_key", None),
            sending_domain=getattr(settings, "mailgun_sending_domain", None),
            api_base=getattr(settings, "mailgun_api_base", None),
        )

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._sending_domain)

    def _ensure(self) -> None:
        if not self.configured:
            raise ProviderNotConfigured("mailgun is not configured")

    # --- inbound side is handled by the webhook, not by polling -----------

    async def list_messages(
        self, *, since: datetime | None
    ) -> list[RawProviderMessage]:
        """Inbound arrives by webhook (`/internal/email/inbound/mailgun`)."""
        return []

    async def get_message(self, provider_message_id: str) -> RawProviderMessage:
        raise ProviderNotConfigured(
            "mailgun inbound is delivered by webhook; messages are not fetched"
        )

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes:
        raise ProviderNotConfigured(
            "mailgun attachments are stored at ingest, not fetched from the API"
        )

    # --- outbound ---------------------------------------------------------

    async def create_draft(self, draft: ProviderDraft) -> str:
        """Mint a local id. Mailgun holds no drafts, so nothing is sent here."""
        self._ensure()
        return f"mailgun-{uuid.uuid4()}"

    async def send_draft(
        self,
        provider_draft_id: str,
        *,
        actor_id: uuid.UUID | None,
        draft: ProviderDraft | None = None,
    ) -> str:
        self._ensure()
        if actor_id is None:
            raise ValueError("actor_id is required to send a draft")
        if draft is None:
            raise ProviderNotConfigured(
                "mailgun keeps no draft; the draft content must be supplied"
            )
        client = await self._client()
        response = await client.post(
            f"{self._api_base}/v3/{self._sending_domain}/messages",
            auth=("api", self._api_key),
            data=_message_fields(draft, sending_domain=self._sending_domain),
            timeout=SEND_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json() if response.content else {}
        return str(payload.get("id") or provider_draft_id)

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS)
        return self._http


def _message_fields(draft: ProviderDraft, *, sending_domain: str) -> dict[str, str]:
    """Mailgun's form fields.

    Recipients are comma-joined rather than repeated keys: httpx only form-encodes
    a mapping, and Mailgun documents a comma-separated `to`.
    """
    sender = draft.from_address or f"noreply@{sending_domain}"
    fields: dict[str, str] = {
        "from": sender,
        "to": ", ".join(draft.to_addresses),
        "subject": draft.subject,
        "text": draft.body_text,
        # Replies must return to the project alias, not to whoever pressed send.
        "h:Reply-To": sender,
    }
    if draft.cc_addresses:
        fields["cc"] = ", ".join(draft.cc_addresses)
    if draft.in_reply_to:
        fields["h:In-Reply-To"] = draft.in_reply_to
    if draft.references:
        fields["h:References"] = " ".join(draft.references)
    return fields
