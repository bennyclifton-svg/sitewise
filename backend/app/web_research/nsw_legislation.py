from __future__ import annotations

import re
from dataclasses import dataclass

from app.web_research.service import WebSearchResult


@dataclass(frozen=True, slots=True)
class _NswLegislationSource:
    title: str
    instrument_id: str
    summary: str
    topics: tuple[str, ...]
    default_rank: int | None = None

    @property
    def url(self) -> str:
        return (
            "https://legislation.nsw.gov.au/view/whole/html/inforce/current/"
            f"{self.instrument_id}"
        )


_SOURCES = (
    _NswLegislationSource(
        title="Environmental Planning and Assessment Act 1979",
        instrument_id="act-1979-203",
        summary="NSW's principal framework for planning, assessment and development consent.",
        topics=(
            "planning approval zoning development application consent assessment",
            "local environmental plan state environmental planning policy",
            "construction certificate occupation certificate",
        ),
        default_rank=0,
    ),
    _NswLegislationSource(
        title="Environmental Planning and Assessment Regulation 2021",
        instrument_id="sl-2021-0759",
        summary="Procedural requirements for development applications and planning assessment.",
        topics=(
            "planning approval development application assessment consent",
            "fees notification exhibition environmental impact statement",
        ),
        default_rank=1,
    ),
    _NswLegislationSource(
        title=(
            "Environmental Planning and Assessment (Development Certification and "
            "Fire Safety) Regulation 2021"
        ),
        instrument_id="sl-2021-0689",
        summary="Certification, occupation certificates and building fire-safety requirements.",
        topics=(
            "building certification construction certificate occupation certificate",
            "fire safety schedule statement class 2 apartment",
        ),
        default_rank=5,
    ),
    _NswLegislationSource(
        title="State Environmental Planning Policy (Housing) 2021",
        instrument_id="epi-2021-0714",
        summary="State planning controls for housing, including specified residential development.",
        topics=(
            "housing apartment residential affordable seniors build to rent",
            "development consent density design",
        ),
        default_rank=2,
    ),
    _NswLegislationSource(
        title="State Environmental Planning Policy (Sustainable Buildings) 2022",
        instrument_id="epi-2022-0521",
        summary="Sustainability, energy, water and embodied-emissions planning requirements.",
        topics=(
            "sustainable building basix energy water thermal performance emissions",
            "apartment residential non residential development",
        ),
        default_rank=3,
    ),
    _NswLegislationSource(
        title=(
            "State Environmental Planning Policy (Exempt and Complying Development "
            "Codes) 2008"
        ),
        instrument_id="epi-2008-0572",
        summary="State-wide exempt and complying development pathways and standards.",
        topics=(
            "exempt complying development code approval certificate",
            "alteration addition dwelling demolition commercial industrial",
        ),
        default_rank=4,
    ),
    _NswLegislationSource(
        title="State Environmental Planning Policy (Transport and Infrastructure) 2021",
        instrument_id="epi-2021-0732",
        summary="Planning controls for infrastructure, transport corridors and adjoining land.",
        topics=(
            "transport infrastructure road rail corridor traffic electricity utility",
            "development referral consultation noise",
        ),
    ),
    _NswLegislationSource(
        title="State Environmental Planning Policy (Resilience and Hazards) 2021",
        instrument_id="epi-2021-0730",
        summary="Planning controls for coastal risks, remediation and hazardous development.",
        topics=(
            "resilience hazard contamination remediation coastal flood risk",
            "development dangerous hazardous material",
        ),
    ),
    _NswLegislationSource(
        title="State Environmental Planning Policy (Biodiversity and Conservation) 2021",
        instrument_id="epi-2021-0722",
        summary="State planning controls for biodiversity, vegetation and environmental areas.",
        topics=(
            "biodiversity conservation vegetation clearing tree koala catchment",
            "environment development",
        ),
    ),
    _NswLegislationSource(
        title="Design and Building Practitioners Act 2020",
        instrument_id="act-2020-007",
        summary="Registration, regulated designs, declarations and duties for building practitioners.",
        topics=(
            "apartment class 2 design practitioner engineer regulated design declaration",
            "building work compliance duty of care construction",
        ),
    ),
    _NswLegislationSource(
        title="Building and Development Certifiers Act 2018",
        instrument_id="act-2018-063",
        summary="Registration, conduct and obligations of building and development certifiers.",
        topics=(
            "building certification certifier principal certifying authority registration",
            "construction occupation certificate strata",
        ),
    ),
    _NswLegislationSource(
        title="Biodiversity Conservation Act 2016",
        instrument_id="act-2016-063",
        summary="NSW biodiversity assessment, conservation and threatened-species framework.",
        topics=(
            "biodiversity threatened species ecological vegetation habitat offset",
            "development assessment clearing environment",
        ),
    ),
    _NswLegislationSource(
        title="Protection of the Environment Operations Act 1997",
        instrument_id="act-1997-156",
        summary="NSW pollution control, environmental protection and licensing framework.",
        topics=(
            "pollution noise waste water air contamination environment licence",
            "construction demolition asbestos incident",
        ),
    ),
    _NswLegislationSource(
        title="Protection of the Environment Operations (General) Regulation 2022",
        instrument_id="sl-2022-0449",
        summary="Detailed environmental-protection and scheduled-activity requirements.",
        topics=(
            "pollution noise waste water air environment scheduled activity licence",
            "construction demolition",
        ),
    ),
    _NswLegislationSource(
        title="Rural Fires Act 1997",
        instrument_id="act-1997-065",
        summary="Bush-fire prevention, protection and approval requirements in NSW.",
        topics=(
            "bush fire bushfire prone land asset protection zone rural fire",
            "development subdivision construction certificate",
        ),
    ),
    _NswLegislationSource(
        title="Heritage Act 1977",
        instrument_id="act-1977-136",
        summary="Protection and approval framework for State heritage items and archaeology.",
        topics=(
            "heritage conservation archaeology excavation state heritage register",
            "development approval alteration demolition",
        ),
    ),
    _NswLegislationSource(
        title="Water Management Act 2000",
        instrument_id="act-2000-092",
        summary="Management of water sources, waterfront land and controlled activities.",
        topics=(
            "water waterfront land controlled activity aquifer drainage river",
            "development construction approval",
        ),
    ),
    _NswLegislationSource(
        title="Home Building Act 1989",
        instrument_id="act-1989-147",
        summary="Residential building contracts, licensing, warranties and insurance requirements.",
        topics=(
            "residential home building contract licence warranty insurance defect",
            "apartment construction contractor owner corporation",
        ),
    ),
    _NswLegislationSource(
        title="Strata Schemes Development Act 2015",
        instrument_id="act-2015-051",
        summary="Creation, subdivision and development of strata schemes.",
        topics=(
            "strata apartment subdivision plan common property development",
            "owners corporation building",
        ),
    ),
    _NswLegislationSource(
        title="Strata Schemes Management Act 2015",
        instrument_id="act-2015-050",
        summary="Management, governance, maintenance and defects for strata schemes.",
        topics=(
            "strata apartment owners corporation defects maintenance building bond",
            "common property developer",
        ),
    ),
)

_QUERY_FILLER_TERMS = {
    "about",
    "applicable",
    "apply",
    "are",
    "current",
    "find",
    "for",
    "is",
    "law",
    "laws",
    "legislation",
    "new",
    "nsw",
    "official",
    "please",
    "project",
    "relevant",
    "requirement",
    "requirements",
    "search",
    "show",
    "south",
    "that",
    "the",
    "this",
    "to",
    "wales",
    "what",
    "which",
}


class NswLegislationProvider:
    """Discover current NSW legislation from an approved official-source registry."""

    async def search(
        self,
        query: str,
        *,
        country: str,
        search_lang: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        del country, search_lang
        query_tokens = _tokens(query)
        specific_tokens = query_tokens - _QUERY_FILLER_TERMS
        if not specific_tokens:
            ranked = sorted(
                (source for source in _SOURCES if source.default_rank is not None),
                key=lambda source: source.default_rank or 0,
            )
        else:
            scored = [
                (_relevance(source, query, specific_tokens), source)
                for source in _SOURCES
            ]
            ranked = [
                source
                for score, source in sorted(
                    scored,
                    key=lambda item: (
                        -item[0],
                        item[1].default_rank
                        if item[1].default_rank is not None
                        else 999,
                        item[1].title,
                    ),
                )
                if score > 0
            ]

        return [
            WebSearchResult(
                url=source.url,
                title=source.title,
                snippet=f"Official NSW legislation registry entry. {source.summary}",
            )
            for source in ranked[:max_results]
        ]


def _relevance(
    source: _NswLegislationSource,
    query: str,
    query_tokens: set[str],
) -> int:
    title_tokens = _tokens(source.title)
    topic_tokens = _tokens(" ".join(source.topics))
    normalized_query = " ".join(query.casefold().split())
    normalized_title = " ".join(source.title.casefold().split())
    exact_title_bonus = 100 if normalized_query == normalized_title else 0
    contained_title_bonus = 30 if normalized_query in normalized_title else 0
    default_bonus = (
        max(0, 6 - source.default_rank)
        if source.default_rank is not None
        else 0
    )
    return (
        exact_title_bonus
        + contained_title_bonus
        + default_bonus
        + 8 * len(query_tokens & title_tokens)
        + 3 * len(query_tokens & topic_tokens)
    )


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))
