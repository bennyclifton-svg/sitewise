from __future__ import annotations

from app.email.providers.base import EmailProvider, ProviderNotConfigured
from app.email.providers.fake import FakeProvider
from app.email.providers.gmail import GmailProvider
from app.email.providers.microsoft_graph import MicrosoftGraphProvider

_FAKE_PROVIDER: FakeProvider | None = None


def email_provider_from_settings(settings) -> EmailProvider:
    name = getattr(settings, "email_provider", "fake")
    if name == "fake":
        global _FAKE_PROVIDER
        if _FAKE_PROVIDER is None:
            _FAKE_PROVIDER = FakeProvider()
        return _FAKE_PROVIDER
    if name == "microsoft_graph":
        provider = MicrosoftGraphProvider.from_settings(settings)
        if not provider.configured:
            raise ProviderNotConfigured("microsoft_graph is not configured")
        return provider
    if name == "gmail":
        provider = GmailProvider.from_settings(settings)
        if not provider.configured:
            raise ProviderNotConfigured("gmail is not configured")
        return provider
    raise ProviderNotConfigured(f"unknown email provider: {name}")


__all__ = [
    "EmailProvider",
    "FakeProvider",
    "GmailProvider",
    "MicrosoftGraphProvider",
    "ProviderNotConfigured",
    "email_provider_from_settings",
]
