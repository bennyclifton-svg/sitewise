from __future__ import annotations

import httpx

from app.web_research.brave import BraveSearchProvider
from tests.conftest import run_async


def test_brave_search_maps_the_external_response_to_web_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == "brave-test-key"
        assert (
            request.url.params["q"]
            == "NSW Housing SEPP alterations additions site:gov.au"
        )
        assert request.url.params["country"] == "AU"
        assert request.url.params["search_lang"] == "en"
        assert request.url.params["count"] == "4"
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714",
                            "title": "State Environmental Planning Policy (Housing) 2021",
                            "description": "Current legislation text.",
                        }
                    ]
                }
            },
        )

    async def run_search():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = BraveSearchProvider(api_key="brave-test-key", client=client)
            return await provider.search(
                "NSW Housing SEPP alterations additions",
                country="AU",
                search_lang="en",
                max_results=4,
            )

    results = run_async(run_search())

    assert len(results) == 1
    assert results[0].title == "State Environmental Planning Policy (Housing) 2021"
    assert results[0].snippet == "Current legislation text."
