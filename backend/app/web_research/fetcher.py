from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin, urlsplit

import httpx

from app.web_research.service import FetchedPage


class WebFetchError(Exception):
    pass


class UnsafeWebUrl(WebFetchError):
    pass


Resolver = Callable[[str], Awaitable[list[str]]]


async def _resolve_public_addresses(host: str) -> list[str]:
    try:
        rows = await asyncio.to_thread(
            socket.getaddrinfo,
            host,
            443,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise WebFetchError(f"could not resolve web source host: {host}") from exc
    return sorted({row[4][0] for row in rows})


def _validated_host(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        raise UnsafeWebUrl("web source URL must use HTTPS")
    if parts.username or parts.password:
        raise UnsafeWebUrl("web source URL must not contain credentials")
    if parts.port not in (None, 443):
        raise UnsafeWebUrl("web source URL must use the standard HTTPS port")
    host = parts.hostname
    if not host:
        raise UnsafeWebUrl("web source URL must contain a host")
    normalized_host = host.lower().rstrip(".")
    if normalized_host != "gov.au" and not normalized_host.endswith(".gov.au"):
        raise UnsafeWebUrl(
            "web source URL must use an official Australian government host"
        )
    return normalized_host


async def _require_public_host(url: str, resolver: Resolver) -> None:
    host = _validated_host(url)
    addresses = await resolver(host)
    if not addresses:
        raise UnsafeWebUrl("web source host did not resolve")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise UnsafeWebUrl("web source host returned an invalid address") from exc
        if not parsed.is_global:
            raise UnsafeWebUrl("web source host must resolve only to public internet addresses")


class SafePageFetcher:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        resolver: Resolver = _resolve_public_addresses,
        timeout_seconds: float = 12.0,
        max_bytes: int = 4 * 1024 * 1024,
        max_redirects: int = 3,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchedPage:
        if self._client is not None:
            return await self._fetch(self._client, url)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._fetch(client, url)

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> FetchedPage:
        current = url
        for redirect_count in range(self._max_redirects + 1):
            await _require_public_host(current, self._resolver)
            try:
                async with client.stream(
                    "GET",
                    current,
                    follow_redirects=False,
                    timeout=self._timeout,
                    headers={
                        "Accept": "text/html, text/plain, application/pdf",
                        "User-Agent": "SiteWise-WebResearch/1.0",
                    },
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebFetchError("web source redirect had no location")
                        if redirect_count >= self._max_redirects:
                            raise WebFetchError("web source exceeded the redirect limit")
                        current = urljoin(str(response.url), location)
                        continue

                    if (
                        response.status_code == 403
                        and response.headers.get("cf-mitigated", "").casefold()
                        == "challenge"
                    ):
                        raise WebFetchError(
                            "official source requires browser verification and "
                            "blocked automated access"
                        )
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(
                        allowed in content_type
                        for allowed in (
                            "text/html",
                            "text/plain",
                            "application/pdf",
                            "application/xml",
                            "text/xml",
                            "application/xhtml+xml",
                        )
                    ):
                        raise WebFetchError(f"unsupported web source content type: {content_type}")
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            declared_size = int(content_length)
                        except ValueError as exc:
                            raise WebFetchError(
                                "web source returned an invalid content length"
                            ) from exc
                        if declared_size > self._max_bytes:
                            raise WebFetchError(
                                "web source exceeds the response size limit"
                            )

                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self._max_bytes:
                            raise WebFetchError("web source exceeds the response size limit")
                        chunks.append(chunk)
                    return FetchedPage(
                        url=str(response.url),
                        content_type=content_type,
                        content=b"".join(chunks),
                    )
            except httpx.HTTPStatusError as exc:
                raise WebFetchError(
                    f"web source returned HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                raise WebFetchError("web source request failed") from exc
        raise WebFetchError("web source exceeded the redirect limit")
