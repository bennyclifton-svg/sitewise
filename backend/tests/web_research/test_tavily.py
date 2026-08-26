from __future__ import annotations

import json

import httpx

from app.web_research.tavily import TavilySearchProvider
from tests.conftest import run_async


def test_tavily_search_maps_the_external_response_to_web_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tavily-test-key"
        payload = json.loads(request.content)
        assert payload == {
            "query": "access consultant Sydney",
            "search_depth": "basic",
            "topic": "general",
            "max_results": 3,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "country": "australia",
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.com/access",
                        "title": " Example  Access Consultants ",
                        "content": " Accessibility   consulting in Sydney. ",
                    }
                ]
            },
        )

    async def run_search():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = TavilySearchProvider(
                api_key="tavily-test-key",
                client=client,
                include_domains=None,
            )
            return await provider.search(
                "access consultant Sydney",
                country="AU",
                search_lang="en",
                max_results=3,
            )

    results = run_async(run_search())

    assert len(results) == 1
    assert results[0].title == "Example Access Consultants"
    assert results[0].snippet == "Accessibility consulting in Sydney."


def test_tavily_search_can_limit_results_to_government_domains() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["include_domains"] == ["gov.au"]
        return httpx.Response(200, json={"results": []})

    async def run_search():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = TavilySearchProvider(api_key="tavily-test-key", client=client)
            return await provider.search(
                "NSW planning guidance",
                country="AU",
                search_lang="en",
                max_results=4,
            )

    assert run_async(run_search()) == []
