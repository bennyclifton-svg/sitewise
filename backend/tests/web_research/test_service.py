from __future__ import annotations

import fitz
import pytest

from app.web_research import FetchedPage, WebResearchService, WebSearchResult
from tests.conftest import run_async


class _SearchProvider:
    async def search(
        self,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        assert query == "Planning Act 2016 development approval"
        assert country == "AU"
        assert search_lang == "en"
        assert max_results == 6
        return [
            WebSearchResult(
                url="https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025",
                title="Planning Act 2016",
                snippet="Current Queensland planning legislation.",
            ),
            WebSearchResult(
                url="https://example.com/planning-act-summary",
                title="Planning Act summary",
                snippet="A secondary summary.",
            ),
            WebSearchResult(
                url="https://legislation.nsw.gov.au/current-act",
                title="NSW planning legislation",
                snippet="Official, but outside the requested jurisdiction.",
            ),
        ]


class _PageFetcher:
    async def fetch(self, url: str) -> FetchedPage:
        assert url == "https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203"
        return FetchedPage(
            url=url,
            content_type="text/html; charset=utf-8",
            content=b"""
                <html><head><title>Environmental Planning and Assessment Act 1979</title></head>
                <body><nav>Navigation</nav><main>
                <h1>Environmental Planning and Assessment Act 1979</h1>
                <p>Current version for 1 July 2026 to date.</p>
                <h2>Section 4.15 Evaluation</h2>
                <p>A consent authority is to take into consideration the relevant matters.</p>
                </main><script>ignore me</script></body></html>
            """,
        )


class _PdfFetcher:
    async def fetch(self, url: str) -> FetchedPage:
        document = fitz.open()
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Planning Regulation 2017\nCurrent as at 18 July 2025\nSchedule 10 Referral agencies",
        )
        content = document.tobytes()
        document.close()
        return FetchedPage(
            url=url,
            content_type="application/pdf",
            content=content,
        )


class _EmptyFetcher:
    async def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(
            url=url,
            content_type="text/html",
            content=b"<html><body><nav>Only navigation</nav></body></html>",
        )


def test_official_search_returns_normalised_government_sources() -> None:
    service = WebResearchService(search_provider=_SearchProvider())

    results = run_async(
        service.search(
            "Planning Act 2016 development approval",
            jurisdiction="QLD",
            max_results=6,
        )
    )

    assert [result.url for result in results] == [
        "https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025"
    ]
    assert results[0].publisher == "Queensland Government"
    assert results[0].jurisdiction == "QLD"
    assert results[0].authority_class == "official_legislation"
    assert results[0].source_type == "web_legislation"


def test_read_official_page_returns_auditable_source_excerpt() -> None:
    service = WebResearchService(
        search_provider=_SearchProvider(),
        page_fetcher=_PageFetcher(),
    )

    source = run_async(
        service.read(
            "https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203",
            section_hint="Section 4.15",
        )
    )

    assert source.title == "Environmental Planning and Assessment Act 1979"
    assert source.publisher == "NSW Government"
    assert source.jurisdiction == "NSW"
    assert source.authority_class == "official_legislation"
    assert source.version_status == "current"
    assert source.effective_date == "1 July 2026"
    assert "Section 4.15 Evaluation" in source.excerpt
    assert "Navigation" not in source.excerpt
    assert "ignore me" not in source.excerpt
    assert len(source.content_hash) == 64
    assert source.retrieved_at.endswith("+00:00")


def test_read_rejects_an_official_page_without_readable_text() -> None:
    service = WebResearchService(
        search_provider=_SearchProvider(),
        page_fetcher=_EmptyFetcher(),
    )

    with pytest.raises(ValueError, match="no readable text"):
        run_async(service.read("https://legislation.nsw.gov.au/empty"))


def test_read_official_pdf_extracts_legislation_text() -> None:
    service = WebResearchService(
        search_provider=_SearchProvider(),
        page_fetcher=_PdfFetcher(),
    )

    source = run_async(
        service.read(
            "https://www.legislation.qld.gov.au/view/pdf/inforce/current/sl-2017-0078",
            section_hint="Schedule 10",
        )
    )

    assert source.title == "Planning Regulation 2017"
    assert source.version_status == "current"
    assert source.effective_date == "18 July 2025"
    assert "Schedule 10 Referral agencies" in source.excerpt
