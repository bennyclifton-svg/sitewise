from __future__ import annotations

from datetime import date
from decimal import Decimal

from tender.schemas import ProjectContext
from tender.services.analysis import (
    AnalysisCell,
    AnalysisCellStatus,
    AnalysisQuote,
    analysis_result_to_json,
    analyse_comparison,
    build_comparable_ledgers,
)
from tender.services.benchmarks import BenchmarkRow


def test_comparable_price_ledger_covers_fill_topup_ranges_and_exclusions() -> None:
    comparison_id = "00000000-0000-0000-0000-000000000001"
    quotes = [
        AnalysisQuote("quote-a", "A Homes", 100_000_000),
        AnalysisQuote("quote-b", "B Homes", 90_000_000),
        AnalysisQuote("quote-c", "C Homes", 95_000_000),
    ]
    cells = [
        AnalysisCell("01.01", "Approval", "approval"),
        AnalysisCell("03.03", "Earthworks", "earthworks"),
        AnalysisCell("06.01", "Roofing", "roofing"),
        AnalysisCell("17.01", "Floor tiles", "tiles"),
        AnalysisCell("18.01", "Cooktop", "cooktop"),
        AnalysisCell("19.01", "Driveway", "driveway"),
        AnalysisCell("20.01", "Connection", "missing"),
    ]
    statuses = [
        _status(comparison_id, "quote-a", "01.01", "excluded_explicit"),
        _status(comparison_id, "quote-a", "03.03", "silent_ambiguous", qa_state="confirmed"),
        _status(comparison_id, "quote-a", "18.01", "pc", amount_cents=200_000),
        _status(comparison_id, "quote-a", "17.01", "ps", amount_cents=200_000),
        _status(comparison_id, "quote-a", "06.01", "excluded_explicit"),
        _status(comparison_id, "quote-a", "20.01", "excluded_explicit"),
        _status(comparison_id, "quote-b", "18.01", "pc", amount_cents=400_000),
        _status(comparison_id, "quote-c", "19.01", "ps", amount_cents=200_000),
    ]

    ledgers = build_comparable_ledgers(
        context=_context(),
        quotes=quotes,
        cells=cells,
        statuses=statuses,
        benchmarks=[
            _benchmark("approval", confidence="high", p25=100_000, p50=150_000, p75=225_000),
            _benchmark("earthworks", confidence="medium", p25=800_000, p50=1_000_000, p75=1_400_000),
            _benchmark("cooktop", confidence="high", p25=300_000, p50=500_000, p75=700_000),
            _benchmark("tiles", confidence="high", metric="per_m2", p25=2_000, p50=3_000, p75=4_000),
            _benchmark("roofing", confidence="low", p25=700_000, p50=900_000, p75=1_200_000),
            _benchmark("driveway", confidence="medium", p25=400_000, p50=600_000, p75=900_000),
        ],
    )

    by_quote = {ledger.quote_id: ledger for ledger in ledgers}

    assert by_quote["quote-a"].comparable_low_cents == 101_650_000
    assert by_quote["quote-a"].comparable_high_cents == 102_250_000
    assert [
        (line.adjustment_type, line.cell_code, line.amount_cents, line.amount_range_cents)
        for line in by_quote["quote-a"].adjustments
    ] == [
        ("fill_at_benchmark", "01.01", 150_000, None),
        ("fill_at_benchmark", "03.03", None, (800_000, 1_400_000)),
        ("allowance_topup", "17.01", 400_000, None),
        ("allowance_topup", "18.01", 300_000, None),
    ]
    assert by_quote["quote-a"].unquantified_items[0].note_key == (
        "analysis.notes.low_confidence_unquantified"
    )
    assert by_quote["quote-a"].notes[0].note_key == "analysis.notes.no_benchmark_available"

    assert by_quote["quote-b"].comparable_low_cents == 90_000_000
    assert by_quote["quote-b"].comparable_high_cents == 90_000_000
    assert by_quote["quote-b"].adjustments == ()

    assert by_quote["quote-c"].comparable_low_cents == 95_200_000
    assert by_quote["quote-c"].comparable_high_cents == 95_700_000
    assert by_quote["quote-c"].adjustments[0].amount_range_cents == (200_000, 700_000)
    assert by_quote["quote-c"].adjustments[0].phrase_key == (
        "claim_strength_by_benchmark_confidence.medium"
    )


def test_per_m2_adjustment_is_skipped_without_floor_area() -> None:
    ledger = build_comparable_ledgers(
        context=_context(floor_area_m2=None),
        quotes=[AnalysisQuote("quote-a", "A Homes", 100_000_000)],
        cells=[AnalysisCell("17.01", "Floor tiles", "tiles")],
        statuses=[_status("comparison", "quote-a", "17.01", "excluded_explicit")],
        benchmarks=[
            _benchmark("tiles", confidence="high", metric="per_m2", p25=2_000, p50=3_000, p75=4_000)
        ],
    )[0]

    assert ledger.comparable_low_cents == 100_000_000
    assert ledger.comparable_high_cents == 100_000_000
    assert ledger.adjustments == ()
    assert ledger.notes[0].note_key == "analysis.notes.floor_area_required"


def test_analysis_result_json_is_stable_for_report_consumers() -> None:
    result = analyse_comparison(
        context=_context(),
        quotes=[AnalysisQuote("quote-a", "A Homes", 100_000_000)],
        cells=[AnalysisCell("01.01", "Approval", "approval")],
        statuses=[_status("comparison", "quote-a", "01.01", "excluded_explicit")],
        benchmarks=[
            _benchmark("approval", confidence="high", p25=100_000, p50=150_000, p75=225_000)
        ],
    )

    assert analysis_result_to_json(result) == {
        "version": 1,
        "gap_matrix": [
            {
                "cell_code": "01.01",
                "cell_name": "Approval",
                "quotes": [
                    {
                        "status": "excluded_explicit",
                        "amount_cents": None,
                        "bundled_into_cell": None,
                        "qa_state": "needs_review",
                        "confidence": None,
                    }
                ],
            }
        ],
        "ledgers": [
            {
                "quote_id": "quote-a",
                "builder_name": "A Homes",
                "stated_total_cents": 100_000_000,
                "comparable_low_cents": 100_150_000,
                "comparable_high_cents": 100_150_000,
                "adjustments": [
                    {
                        "adjustment_type": "fill_at_benchmark",
                        "cell_code": "01.01",
                        "cell_name": "Approval",
                        "status": "excluded_explicit",
                        "amount_cents": 150_000,
                        "amount_range_cents": None,
                        "include_in_headline": True,
                        "phrase_key": "claim_strength_by_benchmark_confidence.high",
                        "benchmark": {
                            "benchmark_id": "approval",
                            "benchmark_key": "approval",
                            "metric": "absolute",
                            "confidence": "high",
                            "source": "model_seed",
                            "provenance": "fixture",
                            "effective_date": "2026-01-01",
                        },
                        "evidence": {
                            "status": "excluded_explicit",
                            "amount_cents": None,
                            "qa_state": "needs_review",
                            "page_refs": [],
                            "source_evidence": {},
                        },
                    }
                ],
                "unquantified_items": [],
                "notes": [],
            }
        ],
        "questions": [],
    }


def _status(
    comparison_id: str,
    quote_id: str,
    cell_code: str,
    status: str,
    *,
    amount_cents: int | None = None,
    qa_state: str = "needs_review",
) -> AnalysisCellStatus:
    return AnalysisCellStatus(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code=cell_code,
        status=status,
        amount_cents=amount_cents,
        qa_state=qa_state,
    )


def _benchmark(
    key: str,
    *,
    confidence: str,
    p25: int,
    p50: int,
    p75: int,
    metric: str = "absolute",
) -> BenchmarkRow:
    return BenchmarkRow(
        id=key,
        benchmark_key=key,
        state="NSW",
        region="metro",
        build_type="new_build",
        spec_level="mid",
        metric=metric,
        p25=Decimal(p25),
        p50=Decimal(p50),
        p75=Decimal(p75),
        unit="AUD",
        source="model_seed",
        provenance="fixture",
        confidence=confidence,
        effective_date=date(2026, 1, 1),
    )


def _context(**overrides: object) -> ProjectContext:
    data = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 1,
        "floor_area_m2": 200,
        "soil_class": "H2",
        "slope_class": "flat",
        "bal_rating": "none",
        "spec_level": "mid",
    }
    data.update(overrides)
    return ProjectContext.model_validate(data)
