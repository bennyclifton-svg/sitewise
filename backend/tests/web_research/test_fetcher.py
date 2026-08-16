from __future__ import annotations

import httpx
import pytest

from app.web_research.fetcher import SafePageFetcher, UnsafeWebUrl, WebFetchError
from tests.conftest import run_async


def test_fetch_rejects_hosts_that_resolve_to_private_addresses() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["127.0.0.1"]

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: None))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(UnsafeWebUrl, match="public internet address"):
            run_async(fetcher.fetch("https://legislation.nsw.gov.au/current"))
    finally:
        run_async(client.aclose())


def test_fetch_revalidates_a_redirect_before_following_it() -> None:
    async def resolve(host: str) -> list[str]:
        return ["127.0.0.1"] if host == "internal.gov.au" else ["1.1.1.1"]

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://internal.gov.au/private"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(UnsafeWebUrl, match="public internet address"):
            run_async(fetcher.fetch("https://legislation.nsw.gov.au/current"))
    finally:
        run_async(client.aclose())


def test_fetch_rejects_a_redirect_outside_official_government_hosts() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["1.1.1.1"]

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "legislation.nsw.gov.au":
            return httpx.Response(302, headers={"location": "https://example.com/page"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="page")

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(UnsafeWebUrl, match="official Australian government"):
            run_async(fetcher.fetch("https://legislation.nsw.gov.au/current"))
    finally:
        run_async(client.aclose())


def test_fetch_rejects_non_https_urls_before_requesting() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["1.1.1.1"]

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: None))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(UnsafeWebUrl, match="must use HTTPS"):
            run_async(fetcher.fetch("http://legislation.nsw.gov.au/current"))
    finally:
        run_async(client.aclose())


def test_fetch_rejects_an_invalid_declared_content_length() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["1.1.1.1"]

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
                "content-length": "not-a-number",
            },
            text="page",
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(WebFetchError, match="invalid content length"):
            run_async(fetcher.fetch("https://legislation.nsw.gov.au/current"))
    finally:
        run_async(client.aclose())


def test_fetch_accepts_official_xml_content_type() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["1.1.1.1"]

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/xml; charset=utf-8"},
            content=b"<exdoc><title>Act</title></exdoc>",
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        page = run_async(
            fetcher.fetch("https://legislation.nsw.gov.au/export/xml/current/act-1979-203")
        )
    finally:
        run_async(client.aclose())

    assert page.content_type.startswith("application/xml")
    assert page.content == b"<exdoc><title>Act</title></exdoc>"


def test_fetch_reports_an_official_site_browser_challenge() -> None:
    async def resolve(_host: str) -> list[str]:
        return ["1.1.1.1"]

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={
                "content-type": "text/html",
                "cf-mitigated": "challenge",
            },
            text="Browser verification required",
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    fetcher = SafePageFetcher(client=client, resolver=resolve)

    try:
        with pytest.raises(WebFetchError, match="browser verification"):
            run_async(
                fetcher.fetch(
                    "https://legislation.nsw.gov.au/view/whole/html/inforce/current/"
                    "act-1979-203"
                )
            )
    finally:
        run_async(client.aclose())
