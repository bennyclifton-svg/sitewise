from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import fitz
from bs4 import BeautifulSoup


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    url: str
    title: str
    snippet: str
    publisher: str | None = None
    jurisdiction: str | None = None
    authority_class: str = "government_guidance"
    source_type: str = "web_reference"


class WebSearchProviderError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FetchedPage:
    url: str
    content_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class WebSource:
    url: str
    title: str
    publisher: str
    jurisdiction: str
    authority_class: str
    source_type: str
    version_status: str
    effective_date: str | None
    section: str | None
    excerpt: str
    content_hash: str
    retrieved_at: str


class SearchProvider(Protocol):
    async def search(
        self,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]: ...


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...


_JURISDICTIONS = {
    "act": ("ACT", "Australian Capital Territory Government"),
    "nsw": ("NSW", "NSW Government"),
    "nt": ("NT", "Northern Territory Government"),
    "qld": ("QLD", "Queensland Government"),
    "sa": ("SA", "South Australian Government"),
    "tas": ("TAS", "Tasmanian Government"),
    "vic": ("VIC", "Victorian Government"),
    "wa": ("WA", "Western Australian Government"),
}


def _source_authority(url: str) -> tuple[str, str, str, str] | None:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    if not host or (host != "gov.au" and not host.endswith(".gov.au")):
        return None

    labels = host.split(".")
    jurisdiction = "CTH"
    publisher = "Australian Government"
    for label, details in _JURISDICTIONS.items():
        if label in labels:
            jurisdiction, publisher = details
            break

    if host.startswith("legislation.") or host == "legislation.gov.au":
        return publisher, jurisdiction, "official_legislation", "web_legislation"
    if "planning" in host or "planningportal" in host:
        return publisher, jurisdiction, "official_planning", "web_planning"
    return publisher, jurisdiction, "government_guidance", "web_reference"


class WebResearchService:
    def __init__(
        self,
        *,
        search_provider: SearchProvider,
        page_fetcher: PageFetcher | None = None,
    ) -> None:
        self._search_provider = search_provider
        self._page_fetcher = page_fetcher

    async def search(
        self,
        query: str,
        *,
        jurisdiction: str | None = None,
        max_results: int = 6,
    ) -> list[WebSearchResult]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("query must not be blank")
        if len(normalized_query) > 300:
            raise ValueError("query must be 300 characters or fewer")

        results = await self._search_provider.search(
            normalized_query,
            country="AU",
            search_lang="en",
            max_results=max(1, min(max_results, 10)),
        )
        requested_jurisdiction = jurisdiction.upper() if jurisdiction else None
        official: list[WebSearchResult] = []
        for result in results:
            if len(result.url) > 2048:
                continue
            authority = _source_authority(result.url)
            if authority is None:
                continue
            publisher, detected_jurisdiction, authority_class, source_type = authority
            if requested_jurisdiction and detected_jurisdiction not in {
                requested_jurisdiction,
                "CTH",
            }:
                continue
            official.append(
                replace(
                    result,
                    title=result.title[:500],
                    snippet=result.snippet[:1000],
                    publisher=publisher,
                    jurisdiction=detected_jurisdiction,
                    authority_class=authority_class,
                    source_type=source_type,
                )
            )
        return official

    async def read(self, url: str, *, section_hint: str | None = None) -> WebSource:
        if len(url) > 2048:
            raise ValueError("web source URL must be 2048 characters or fewer")
        normalized_section = section_hint.strip() if section_hint else None
        normalized_section = normalized_section or None
        if normalized_section and len(normalized_section) > 200:
            raise ValueError("section hint must be 200 characters or fewer")
        authority = _source_authority(url)
        if authority is None:
            raise ValueError("web source must be an official Australian government URL")
        if self._page_fetcher is None:
            raise RuntimeError("web page fetcher is not configured")

        page = await self._page_fetcher.fetch(url)
        final_authority = _source_authority(page.url)
        if final_authority is None:
            raise ValueError("web source redirected outside official Australian government sites")
        publisher, jurisdiction, authority_class, source_type = final_authority
        if "application/pdf" in page.content_type.casefold():
            title, text = await asyncio.to_thread(_extract_pdf, page.content)
        else:
            title, text = _extract_html(page.content)
        if not text.strip():
            raise ValueError("web source contained no readable text")
        excerpt = _bounded_excerpt(text, section_hint=normalized_section)
        return WebSource(
            url=_canonical_url(page.url),
            title=title[:500],
            publisher=publisher,
            jurisdiction=jurisdiction,
            authority_class=authority_class,
            source_type=source_type,
            version_status=_version_status(text),
            effective_date=_effective_date(text),
            section=normalized_section,
            excerpt=excerpt,
            content_hash=hashlib.sha256(page.content).hexdigest(),
            retrieved_at=datetime.now(UTC).isoformat(),
        )


def _extract_html(content: bytes) -> tuple[str, str]:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "nav", "form", "noscript"]):
        element.decompose()
    title = " ".join((soup.title.get_text(" ", strip=True) if soup.title else "").split())
    body = soup.find("main") or soup.find("article") or soup.body or soup
    text = "\n".join(
        line for line in (" ".join(item.split()) for item in body.get_text("\n").splitlines()) if line
    )
    if not title:
        heading = body.find("h1")
        title = " ".join(heading.get_text(" ", strip=True).split()) if heading else "Official source"
    return title, text


def _extract_pdf(content: bytes) -> tuple[str, str]:
    document = fitz.open(stream=content, filetype="pdf")
    try:
        pages: list[str] = []
        total_chars = 0
        for page in document:
            page_text = page.get_text("text").strip()
            if page_text:
                pages.append(page_text)
                total_chars += len(page_text)
            if total_chars >= 50_000:
                break
    finally:
        document.close()
    text = "\n".join(pages)
    title = next((" ".join(line.split()) for line in text.splitlines() if line.strip()), "Official PDF")
    return title, text


def _bounded_excerpt(text: str, *, section_hint: str | None, max_chars: int = 12_000) -> str:
    if not section_hint or not section_hint.strip():
        return text[:max_chars]
    index = text.casefold().find(section_hint.strip().casefold())
    if index < 0:
        return text[:max_chars]
    start = max(0, index - 300)
    return text[start : start + max_chars]


def _version_status(text: str) -> str:
    lowered = text.casefold()
    if any(marker in lowered for marker in ("not authorised", "unofficial", "indicative only")):
        return "unofficial"
    if any(marker in lowered for marker in ("not in force", "repealed", "revoked")):
        return "historical"
    if "as made" in lowered:
        return "as_made"
    if any(marker in lowered for marker in ("current version", "current as at", "latest version", "in force")):
        return "current"
    return "unknown"


_EFFECTIVE_DATE_RE = re.compile(
    r"(?:current version for|current as at|latest version(?:\s+\w+)?)[^\d]{0,20}"
    r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.IGNORECASE,
)


def _effective_date(text: str) -> str | None:
    match = _EFFECTIVE_DATE_RE.search(text)
    return match.group(1) if match else None


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
