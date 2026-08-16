from __future__ import annotations

from app.web_research.nsw_legislation import (
    NswLegislationProvider,
    instrument_id_from_url,
    xml_export_url,
)
from tests.conftest import run_async


def _search(query: str, *, max_results: int = 6):
    return run_async(
        NswLegislationProvider().search(
            query,
            country="AU",
            search_lang="en",
            max_results=max_results,
        )
    )


def test_nsw_provider_ranks_inner_west_lep_for_an_lga_query() -> None:
    results = _search("Inner West local environmental plan heritage conservation")

    assert results[0].title == "Inner West Local Environmental Plan 2022"
    assert results[0].url.endswith("/epi-2022-0457")


def test_nsw_provider_ranks_core_planning_legislation_for_a_topic_query() -> None:
    results = _search("planning approval zoning development application")

    titles = [result.title for result in results]
    assert titles[:2] == [
        "Environmental Planning and Assessment Act 1979",
        "Environmental Planning and Assessment Regulation 2021",
    ]
    assert all(result.url.startswith("https://legislation.nsw.gov.au/") for result in results)


def test_nsw_provider_ranks_an_exact_instrument_title_first() -> None:
    results = _search("State Environmental Planning Policy Housing 2021")

    assert results[0].title == "State Environmental Planning Policy (Housing) 2021"
    assert results[0].url.endswith("/epi-2021-0714")


def test_nsw_provider_uses_core_sources_for_a_generic_applicability_query() -> None:
    results = _search("what legislation is applicable to this NSW project")

    assert [result.title for result in results[:2]] == [
        "Environmental Planning and Assessment Act 1979",
        "Environmental Planning and Assessment Regulation 2021",
    ]


def test_nsw_xml_export_url_for_an_instrument() -> None:
    assert xml_export_url("act-1979-203") == (
        "https://legislation.nsw.gov.au/export/xml/current/act-1979-203"
    )


def test_instrument_id_from_legislation_html_url() -> None:
    assert (
        instrument_id_from_url(
            "https://legislation.nsw.gov.au/view/whole/html/inforce/current/"
            "act-1979-203"
        )
        == "act-1979-203"
    )
    assert (
        instrument_id_from_url(
            "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457"
        )
        == "epi-2022-0457"
    )
    assert (
        instrument_id_from_url(
            "https://legislation.nsw.gov.au/export/xml/current/sl-2021-0759"
        )
        == "sl-2021-0759"
    )
    assert instrument_id_from_url("https://www.innerwest.nsw.gov.au/dcp.pdf") is None


def test_nsw_provider_respects_the_result_limit() -> None:
    results = _search("apartment building design certification", max_results=3)

    assert len(results) == 3
    assert "Design and Building Practitioners Act 2020" in {
        result.title for result in results
    }
