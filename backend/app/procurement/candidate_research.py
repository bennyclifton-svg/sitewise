"""Commercial web discovery for Procurement Strategy candidates.

This is intentionally separate from the official-government research service:
candidate results are commercial discovery leads, never project evidence or
construction guidance.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.config import settings
from app.sitewise.discipline_catalog import discipline_by_code
from app.web_research.brave import BraveSearchProvider
from app.web_research.factory import WebResearchDisabled
from app.web_research.service import SearchProvider, WebSearchResult


class ProcurementCandidateResearch:
    def __init__(self, *, search_provider: SearchProvider) -> None:
        self._search_provider = search_provider

    async def search(
        self,
        *,
        discipline_code: str,
        location: str | None = None,
        max_results: int = 8,
    ) -> dict[str, Any]:
        discipline = discipline_by_code(discipline_code)
        normalized_location = " ".join((location or "Australia").split())
        if len(normalized_location) > 120:
            raise ValueError("location must be 120 characters or fewer")
        result_limit = max(1, min(max_results, 10))
        role = {
            "consultant": "consultant",
            "trade": "contractor",
            "supplier": "supplier",
        }[discipline.participant_type]
        query = f"{discipline.pmp_label} {role} {normalized_location} company services"
        raw_results = await self._search_provider.search(
            query,
            country="AU",
            search_lang="en",
            max_results=result_limit,
        )
        results = [_commercial_result(result) for result in raw_results]
        return {
            "discipline_code": discipline.code,
            "discipline_label": discipline.pmp_label,
            "location": normalized_location,
            "query": query,
            "results": results,
            "disclaimer": (
                "Discovery leads only. Verify capability, capacity, conflicts, "
                "licensing and insurance before issuing a request."
            ),
        }


def _commercial_result(result: WebSearchResult) -> dict[str, Any]:
    payload = asdict(result)
    payload.update(
        authority_class="commercial_discovery",
        source_type="candidate_web_result",
        publisher=None,
        jurisdiction=None,
    )
    payload["title"] = result.title[:500]
    payload["snippet"] = result.snippet[:1000]
    payload["url"] = result.url[:2048]
    return payload


def get_procurement_candidate_research() -> ProcurementCandidateResearch:
    if not settings.agent_web_research_enabled:
        raise WebResearchDisabled(
            "Commercial candidate research is not configured for this deployment. "
            "This does not affect existing Tenderer slots; read the Procurement "
            "Strategy and continue with project appointment facts or user-provided firms."
        )
    if settings.web_search_provider != "brave" or not settings.brave_search_api_key:
        raise WebResearchDisabled(
            "Commercial candidate research requires a configured Brave search provider. "
            "This does not affect existing Tenderer slots; read the Procurement "
            "Strategy and continue with project appointment facts or user-provided firms."
        )
    return ProcurementCandidateResearch(
        search_provider=BraveSearchProvider(
            api_key=settings.brave_search_api_key,
            timeout_seconds=settings.web_fetch_timeout_seconds,
            site_filter=None,
        )
    )
