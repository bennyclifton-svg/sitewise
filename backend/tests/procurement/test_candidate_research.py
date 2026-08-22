from __future__ import annotations

import pytest

from app.config import settings
from app.procurement.candidate_research import (
    ProcurementCandidateResearch,
    get_procurement_candidate_research,
)
from app.web_research.factory import WebResearchDisabled
from app.web_research.service import WebSearchResult
from tests.conftest import run_async


class _Provider:
    def __init__(self) -> None:
        self.call = None

    async def search(self, query, *, country, search_lang, max_results):
        self.call = (query, country, search_lang, max_results)
        return [
            WebSearchResult(
                url="https://example.com/structural",
                title="Example Structural Engineers",
                snippet="Structural engineering services in Sydney.",
            )
        ]


def test_candidate_research_uses_canonical_discipline_and_marks_leads() -> None:
    provider = _Provider()
    service = ProcurementCandidateResearch(search_provider=provider)

    result = run_async(
        service.search(
            discipline_code="consultant.structural",
            location="Sydney NSW",
            max_results=3,
        )
    )

    assert provider.call == (
        "Structural consultant Sydney NSW company services",
        "AU",
        "en",
        3,
    )
    assert result["discipline_label"] == "Structural"
    assert result["results"][0]["source_type"] == "candidate_web_result"
    assert "Discovery leads only" in result["disclaimer"]


def test_disabled_candidate_research_distinguishes_config_from_table_capacity(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "agent_web_research_enabled", False)

    with pytest.raises(WebResearchDisabled, match="does not affect existing Tenderer slots"):
        get_procurement_candidate_research()
