from __future__ import annotations

import httpx
from app.agent.observability import provider_span

from app.web_research.service import WebSearchProviderError, WebSearchResult


_COUNTRY_NAMES = {
    "AU": "australia",
}


class TavilySearchProvider:
    _URL = "https://api.tavily.com/search"

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        include_domains: tuple[str, ...] | None = ("gov.au",),
    ) -> None:
        if not api_key.strip():
            raise ValueError("Tavily API key must not be blank")
        self._api_key = api_key
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._include_domains = include_domains

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

    @provider_span("tavily", "search")
    async def _search(
        self,
        client: httpx.AsyncClient,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        payload: dict[str, object] = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        country_name = _COUNTRY_NAMES.get(country.upper())
        if country_name:
            payload["country"] = country_name
        if self._include_domains:
            payload["include_domains"] = list(self._include_domains)
        if search_lang.lower() != "en":
            payload["query"] = f"{query} language:{search_lang.lower()}"

        try:
            response = await client.post(
                self._URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            response_payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchProviderError("web search provider request failed") from exc

        raw_results = (
            response_payload.get("results")
            if isinstance(response_payload, dict)
            else None
        )
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
            content = item.get("content")
            results.append(
                WebSearchResult(
                    url=url,
                    title=" ".join(title.split()),
                    snippet=(
                        " ".join(content.split()) if isinstance(content, str) else ""
                    ),
                )
            )
        return results
