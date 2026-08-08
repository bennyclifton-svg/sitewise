from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.web_research.brave import BraveSearchProvider
from app.web_research.fetcher import SafePageFetcher
from app.web_research.nsw_legislation import NswLegislationProvider
from app.web_research.service import SearchProvider, WebResearchService


class WebResearchDisabled(Exception):
    pass


@lru_cache(maxsize=1)
def get_web_research_service() -> WebResearchService:
    if not settings.agent_web_research_enabled:
        raise WebResearchDisabled("Web research is not enabled for this deployment")
    return WebResearchService(
        search_provider=_search_provider(),
        page_fetcher=SafePageFetcher(
            timeout_seconds=settings.web_fetch_timeout_seconds,
            max_bytes=settings.web_fetch_max_bytes,
        ),
    )


def _search_provider() -> SearchProvider:
    if settings.web_search_provider == "nsw_legislation":
        return NswLegislationProvider()
    if settings.web_search_provider == "brave" and settings.brave_search_api_key:
        return BraveSearchProvider(
            api_key=settings.brave_search_api_key,
            timeout_seconds=settings.web_fetch_timeout_seconds,
        )
    raise WebResearchDisabled("Web research provider is not configured")
