from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

import httpx

from app.email.providers.base import ProviderNotConfigured
from app.email.schemas import ProviderDraft, RawProviderAttachment, RawProviderMessage

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailProvider:
    name = "gmail"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id or ""
        self._client_secret = client_secret or ""
        self._refresh_token = refresh_token or ""
        self._http = http
        self._token: str | None = None

    @classmethod
    def from_settings(cls, settings) -> "GmailProvider":
        return cls(
            client_id=getattr(settings, "gmail_client_id", None),
            client_secret=getattr(settings, "gmail_client_secret", None),
            refresh_token=getattr(settings, "gmail_refresh_token", None),
        )

    @property
    def configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._refresh_token)

    def _ensure(self) -> None:
        if not self.configured:
            raise ProviderNotConfigured("gmail is not configured")

    async def list_messages(
        self, *, since: datetime | None
    ) -> list[RawProviderMessage]:
        self._ensure()
        params: dict[str, str] = {"maxResults": "50"}
        if since is not None:
            params["q"] = f"after:{int(since.timestamp())}"
        listing = await self._request("GET", "/users/me/messages", params=params)
        messages: list[RawProviderMessage] = []
        for item in listing.get("messages") or []:
            if isinstance(item, dict) and item.get("id"):
                messages.append(await self.get_message(str(item["id"])))
        return messages

    async def get_message(self, provider_message_id: str) -> RawProviderMessage:
        self._ensure()
        payload = await self._request(
            "GET",
            f"/users/me/messages/{provider_message_id}",
            params={"format": "full"},
        )
        return _gmail_message(payload)

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes:
        self._ensure()
        payload = await self._request(
            "GET",
            f"/users/me/messages/{provider_message_id}/attachments/{attachment_id}",
        )
        data = payload.get("data")
        if not data:
            return b""
        return base64.urlsafe_b64decode(str(data) + "=" * (-len(str(data)) % 4))

    async def create_draft(self, draft: ProviderDraft) -> str:
        self._ensure()
        payload = await self._request(
            "POST",
            "/users/me/drafts",
            json={"message": {"raw": _gmail_raw(draft)}},
        )
        draft_id = payload.get("id")
        if not draft_id:
            raise ProviderNotConfigured("gmail draft create returned no id")
        return str(draft_id)

    async def send_draft(
        self, provider_draft_id: str, *, actor_id: uuid.UUID | None
    ) -> str:
        self._ensure()
        if actor_id is None:
            raise ValueError("actor_id is required to send a draft")
        payload = await self._request(
            "POST",
            f"/users/me/drafts/{provider_draft_id}/send",
            json={},
        )
        return str(payload.get("id") or provider_draft_id)

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def _access_token(self) -> str:
        if self._token:
            return self._token
        client = await self._client()
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ProviderNotConfigured("gmail token response had no access_token")
        self._token = str(token)
        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._client()
        token = await self._access_token()
        response = await client.request(
            method,
            f"{GMAIL_API}{path}",
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


def _gmail_raw(draft: ProviderDraft) -> str:
    message = EmailMessage()
    message["To"] = ", ".join(draft.to_addresses)
    if draft.cc_addresses:
        message["Cc"] = ", ".join(draft.cc_addresses)
    message["Subject"] = draft.subject
    if draft.in_reply_to:
        message["In-Reply-To"] = draft.in_reply_to
    message.set_content(draft.body_text)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return encoded.rstrip("=")


def _gmail_header(payload: dict[str, Any], name: str) -> str:
    headers = payload.get("headers")
    if not isinstance(headers, list):
        return ""
    lowered = name.lower()
    for item in headers:
        if isinstance(item, dict) and str(item.get("name", "")).lower() == lowered:
            return str(item.get("value") or "")
    return ""


def _gmail_message(payload: dict[str, Any]) -> RawProviderMessage:
    inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    headers = {}
    raw_headers = inner.get("headers")
    if isinstance(raw_headers, list):
        for item in raw_headers:
            if isinstance(item, dict) and item.get("name"):
                headers[str(item["name"])] = str(item.get("value") or "")
    attachments: list[RawProviderAttachment] = []
    for part in inner.get("parts") or []:
        if not isinstance(part, dict):
            continue
        body = part.get("body") if isinstance(part.get("body"), dict) else {}
        attachment_id = body.get("attachmentId")
        if not attachment_id:
            continue
        attachments.append(
            RawProviderAttachment(
                provider_attachment_id=str(attachment_id),
                filename=str(part.get("filename") or "attachment"),
                content_type=str(part.get("mimeType") or "application/octet-stream"),
                size_bytes=int(body.get("size") or 0),
            )
        )
    sent_at = None
    internal = payload.get("internalDate")
    if internal:
        sent_at = datetime.fromtimestamp(int(internal) / 1000, tz=UTC)
    body_text = payload.get("snippet") or ""
    return RawProviderMessage(
        provider="gmail",
        provider_message_id=str(payload.get("id") or ""),
        provider_thread_id=payload.get("threadId"),
        internet_message_id=_gmail_header(inner, "Message-ID") or None,
        from_address=_gmail_header(inner, "From") or "unknown@example.com",
        to_addresses=[addr.strip() for addr in _gmail_header(inner, "To").split(",") if addr.strip()],
        cc_addresses=[addr.strip() for addr in _gmail_header(inner, "Cc").split(",") if addr.strip()],
        subject=_gmail_header(inner, "Subject"),
        sent_at=sent_at,
        body_text=str(body_text),
        headers=headers,
        attachments=attachments,
    )
