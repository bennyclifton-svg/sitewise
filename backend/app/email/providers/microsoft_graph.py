from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.email.providers.base import ProviderNotConfigured
from app.email.schemas import ProviderDraft, RawProviderAttachment, RawProviderMessage

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphProvider:
    name = "microsoft_graph"

    def __init__(
        self,
        *,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        mailbox_user: str | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._tenant_id = tenant_id or ""
        self._client_id = client_id or ""
        self._client_secret = client_secret or ""
        self._refresh_token = refresh_token or ""
        self._mailbox_user = mailbox_user or ""
        self._http = http
        self._token: str | None = None

    @classmethod
    def from_settings(cls, settings) -> "MicrosoftGraphProvider":
        return cls(
            tenant_id=getattr(settings, "microsoft_graph_tenant_id", None),
            client_id=getattr(settings, "microsoft_graph_client_id", None),
            client_secret=getattr(settings, "microsoft_graph_client_secret", None),
            refresh_token=getattr(settings, "microsoft_graph_refresh_token", None),
            mailbox_user=getattr(settings, "microsoft_graph_mailbox_user", None),
        )

    @property
    def configured(self) -> bool:
        return bool(self._tenant_id and self._client_id and self._client_secret)

    def _ensure(self) -> None:
        if not self.configured:
            raise ProviderNotConfigured("microsoft_graph is not configured")

    def _user_path(self) -> str:
        if self._mailbox_user:
            return f"/users/{quote(self._mailbox_user)}"
        return "/me"

    async def list_messages(
        self, *, since: datetime | None
    ) -> list[RawProviderMessage]:
        self._ensure()
        params: dict[str, str] = {
            "$select": (
                "id,conversationId,internetMessageId,subject,from,toRecipients,"
                "ccRecipients,body,sentDateTime,internetMessageHeaders,hasAttachments"
            ),
            "$top": "50",
        }
        if since is not None:
            params["$filter"] = f"receivedDateTime ge {since.isoformat()}"
        payload = await self._request("GET", f"{self._user_path()}/messages", params=params)
        return [_graph_message(item) for item in payload.get("value", [])]

    async def get_message(self, provider_message_id: str) -> RawProviderMessage:
        self._ensure()
        payload = await self._request(
            "GET",
            f"{self._user_path()}/messages/{quote(provider_message_id)}",
            params={"$expand": "attachments($select=id,name,contentType,size)"},
        )
        return _graph_message(payload)

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes:
        self._ensure()
        return await self._request_bytes(
            "GET",
            f"{self._user_path()}/messages/{quote(provider_message_id)}"
            f"/attachments/{quote(attachment_id)}/$value",
        )

    async def create_draft(self, draft: ProviderDraft) -> str:
        self._ensure()
        payload = await self._request(
            "POST",
            f"{self._user_path()}/messages",
            json={
                "subject": draft.subject,
                "body": {"contentType": "Text", "content": draft.body_text},
                "toRecipients": [_graph_recipient(addr) for addr in draft.to_addresses],
                "ccRecipients": [_graph_recipient(addr) for addr in draft.cc_addresses],
            },
        )
        draft_id = payload.get("id")
        if not draft_id:
            raise ProviderNotConfigured("microsoft_graph draft create returned no id")
        return str(draft_id)

    async def send_draft(
        self, provider_draft_id: str, *, actor_id: uuid.UUID | None
    ) -> str:
        self._ensure()
        if actor_id is None:
            raise ValueError("actor_id is required to send a draft")
        await self._request(
            "POST",
            f"{self._user_path()}/messages/{quote(provider_draft_id)}/send",
        )
        return provider_draft_id

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def _access_token(self) -> str:
        if self._token:
            return self._token
        client = await self._client()
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        if self._refresh_token:
            data["grant_type"] = "refresh_token"
            data["refresh_token"] = self._refresh_token
        else:
            data["grant_type"] = "client_credentials"
        response = await client.post(
            f"https://login.microsoftonline.com/{quote(self._tenant_id)}/oauth2/v2.0/token",
            data=data,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ProviderNotConfigured("microsoft_graph token response had no access_token")
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
            f"{GRAPH_BASE}{path}",
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    async def _request_bytes(self, method: str, path: str) -> bytes:
        client = await self._client()
        token = await self._access_token()
        response = await client.request(
            method,
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.content


def _graph_recipient(address: str) -> dict[str, Any]:
    return {"emailAddress": {"address": address}}


def _graph_address(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    email = node.get("emailAddress") if isinstance(node.get("emailAddress"), dict) else node
    if isinstance(email, dict):
        return str(email.get("address") or "")
    return ""


def _graph_message(payload: dict[str, Any]) -> RawProviderMessage:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
    headers = {}
    raw_headers = payload.get("internetMessageHeaders")
    if isinstance(raw_headers, list):
        for item in raw_headers:
            if isinstance(item, dict) and item.get("name"):
                headers[str(item["name"])] = str(item.get("value") or "")
    attachments = []
    raw_attachments = payload.get("attachments")
    if isinstance(raw_attachments, list):
        for item in raw_attachments:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            attachments.append(
                RawProviderAttachment(
                    provider_attachment_id=str(item["id"]),
                    filename=str(item.get("name") or "attachment"),
                    content_type=str(item.get("contentType") or "application/octet-stream"),
                    size_bytes=int(item.get("size") or 0),
                )
            )
    sent_at = None
    if payload.get("sentDateTime"):
        sent_at = datetime.fromisoformat(str(payload["sentDateTime"]).replace("Z", "+00:00"))
    return RawProviderMessage(
        provider="microsoft_graph",
        provider_message_id=str(payload.get("id") or ""),
        provider_thread_id=payload.get("conversationId"),
        internet_message_id=payload.get("internetMessageId"),
        from_address=_graph_address(payload.get("from")),
        to_addresses=[
            addr
            for addr in (
                _graph_address(item) for item in (payload.get("toRecipients") or [])
            )
            if addr
        ],
        cc_addresses=[
            addr
            for addr in (
                _graph_address(item) for item in (payload.get("ccRecipients") or [])
            )
            if addr
        ],
        subject=str(payload.get("subject") or ""),
        sent_at=sent_at,
        body_text=str(body.get("content") or ""),
        headers=headers,
        attachments=attachments,
    )
