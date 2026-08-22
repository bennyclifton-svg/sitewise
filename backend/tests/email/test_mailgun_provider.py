"""Outbound send through Mailgun, from the project's own address."""

from __future__ import annotations

import uuid

import httpx
import pytest

from app.email.providers import email_provider_from_settings
from app.email.providers.base import ProviderNotConfigured
from app.email.providers.mailgun_send import MailgunProvider
from app.email.schemas import ProviderDraft

ACTOR = uuid.UUID("22222222-2222-2222-2222-222222222222")


class _Settings:
    """Minimal stand-in for app settings."""

    def __init__(self, **kwargs: object) -> None:
        self.email_provider = "mailgun"
        self.mailgun_api_key = "key-test"
        self.mailgun_sending_domain = "sitewise.au"
        self.mailgun_api_base = "https://api.mailgun.net"
        self.environment = "development"
        for key, value in kwargs.items():
            setattr(self, key, value)


def _provider(handler) -> MailgunProvider:
    transport = httpx.MockTransport(handler)
    return MailgunProvider(
        api_key="key-test",
        sending_domain="sitewise.au",
        api_base="https://api.mailgun.net",
        http=httpx.AsyncClient(transport=transport),
    )


def _draft(**kwargs: object) -> ProviderDraft:
    payload: dict = {
        "to_addresses": ["builder@example.com"],
        "subject": "Newtown Extension — RFI 004",
        "body_text": "Please confirm the slab set-out.",
        "from_address": "newtown-extension-2@sitewise.au",
    }
    payload.update(kwargs)
    return ProviderDraft(**payload)


# --- configuration -------------------------------------------------------


def test_provider_is_unconfigured_without_an_api_key() -> None:
    assert not MailgunProvider(api_key="", sending_domain="sitewise.au").configured


def test_settings_factory_builds_a_mailgun_provider() -> None:
    provider = email_provider_from_settings(_Settings())
    assert isinstance(provider, MailgunProvider)


def test_settings_factory_rejects_an_unconfigured_mailgun() -> None:
    with pytest.raises(ProviderNotConfigured):
        email_provider_from_settings(_Settings(mailgun_api_key=None))


# --- the fake provider must never be reachable in production -------------


def test_fake_provider_is_refused_in_production() -> None:
    settings = _Settings(email_provider="fake", environment="production")
    with pytest.raises(ProviderNotConfigured, match="fake"):
        email_provider_from_settings(settings)


def test_fake_provider_is_allowed_in_development() -> None:
    settings = _Settings(email_provider="fake", environment="development")
    assert email_provider_from_settings(settings).name == "fake"


# --- drafting ------------------------------------------------------------


@pytest.mark.anyio
async def test_create_draft_does_not_call_mailgun() -> None:
    """Mailgun has no server-side drafts; creating one must stay local."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"id": "<nope@sitewise.au>"})

    draft_id = await _provider(handler).create_draft(_draft())
    assert calls == []
    assert draft_id.startswith("mailgun-")


# --- sending -------------------------------------------------------------


@pytest.mark.anyio
async def test_send_posts_to_the_sending_domain_with_basic_auth() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"id": "<20260822.abc@sitewise.au>"})

    message_id = await _provider(handler).send_draft(
        "mailgun-1", actor_id=ACTOR, draft=_draft()
    )

    assert seen["url"] == "https://api.mailgun.net/v3/sitewise.au/messages"
    assert seen["auth"].startswith("Basic ")
    assert message_id == "<20260822.abc@sitewise.au>"


@pytest.mark.anyio
async def test_send_uses_the_project_address_as_from_and_reply_to() -> None:
    """This is what makes a reply come back into the project."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"id": "<x@sitewise.au>"})

    await _provider(handler).send_draft("mailgun-1", actor_id=ACTOR, draft=_draft())

    body = seen["body"]
    assert "newtown-extension-2%40sitewise.au" in body
    assert "h%3AReply-To" in body


@pytest.mark.anyio
async def test_send_carries_threading_headers() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"id": "<x@sitewise.au>"})

    await _provider(handler).send_draft(
        "mailgun-1",
        actor_id=ACTOR,
        draft=_draft(
            in_reply_to="<original@builder.example.com>",
            references=["<first@builder.example.com>"],
        ),
    )

    body = seen["body"]
    assert "h%3AIn-Reply-To" in body
    assert "h%3AReferences" in body


@pytest.mark.anyio
async def test_send_requires_an_actor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "<x@sitewise.au>"})

    with pytest.raises(ValueError, match="actor_id"):
        await _provider(handler).send_draft("mailgun-1", actor_id=None, draft=_draft())


@pytest.mark.anyio
async def test_send_without_a_draft_payload_is_refused() -> None:
    """Mailgun keeps no draft, so the caller must supply the content."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "<x@sitewise.au>"})

    with pytest.raises(ProviderNotConfigured, match="draft"):
        await _provider(handler).send_draft("mailgun-1", actor_id=ACTOR, draft=None)


@pytest.mark.anyio
async def test_a_mailgun_rejection_surfaces_as_an_error() -> None:
    """A failed send must raise so the draft lands in send_failed, not sent."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid private key"})

    with pytest.raises(httpx.HTTPStatusError):
        await _provider(handler).send_draft(
            "mailgun-1", actor_id=ACTOR, draft=_draft()
        )
