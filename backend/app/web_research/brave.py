from __future__ import annotations

import httpx

from app.web_research.service import WebSearchProviderError, WebSearchResult


class BraveSearchProvider:
    _URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        site_filter: str | None = "gov.au",
    ) -> None:
        if not api_key.strip():
            raise ValueError("Brave Search API key must not be blank")
        self._api_key = api_key
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._site_filter = site_filter.strip() if site_filter else None

    async def search(
        self,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        if self._client is not None:
            return await self._search(
                self._client,
                query,
                country=country,
                search_lang=search_lang,
                max_results=max_results,
            )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._search(
                client,
                query,
                country=country,
                search_lang=search_lang,
                max_results=max_results,
            )

    async def _search(
        self,
        client: httpx.AsyncClient,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        try:
            response = await client.get(
                self._URL,
                params={
                    "q": (
                        f"{query} site:{self._site_filter}"
                        if self._site_filter
                        else query
                    ),
                    "country": country,
                    "search_lang": search_lang,
                    "count": max_results,
                    "safesearch": "moderate",
                },
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchProviderError("web search provider request failed") from exc

        web = payload.get("web") if isinstance(payload, dict) else None
        raw_results = web.get("results") if isinstance(web, dict) else None
        if not isinstance(raw_results, list):
            return []

        results: list[WebSearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            title = item.get("title")
            if not isinstance(url, str) or not isinstance(title, str):
                continue
            description = item.get("description")
            results.append(
                WebSearchResult(
                    url=url,
                    title=" ".join(title.split()),
                    snippet=(
                        " ".join(description.split())
                        if isinstance(description, str)
                        else ""
                    ),
                )
            )
        return results
