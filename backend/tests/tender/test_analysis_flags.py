from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from tender.schemas import ProjectContext
from tender.services.analysis import (
    AnalysisCell,
    AnalysisCellStatus,
    AnalysisFlagDraft,
    AnalysisQuote,
    build_gap_matrix,
    generate_analysis_flags,
    merge_generated_flags,
)
from tender.services.benchmarks import BenchmarkRow


@pytest.mark.parametrize(
    ("confidence", "allowance_cents", "expected_severity", "include_in_report"),
    [
        ("high", 790, "caution", True),
        ("high", 700, "warning", True),
        ("medium", 700, "warning", True),
        ("low", 700, "info", False),
    ],
)
def test_allowance_flag_severity_scales_by_gap_and_confidence(
    confidence: str,
    allowance_cents: int,
    expected_severity: str,
    include_in_report: bool,
) -> None:
    flags = generate_analysis_flags(
        context=_context(),
        quotes=[AnalysisQuote("quote-a", "A Homes", 1_000_000)],
        cells=[AnalysisCell("18.01", "Cooktop", "cooktop")],
        statuses=[
            _status(
                "quote-a",
                "18.01",
                "pc",
                amount_cents=allowance_cents,
            )
        ],
        benchmarks=[
            _benchmark(
                "cooktop",
                confidence=confidence,
                p25=800,
                p50=1_000,
                p75=1_300,
            )
        ],
    )

    flag = next(flag for flag in flags if flag.flag_type == "low_pc_allowance")
    assert flag.severity == expected_severity
    assert flag.include_in_report is include_in_report
    assert flag.evidence["allowance_cents"] == allowance_cents
    assert flag.evidence["benchmark"]["confidence"] == confidence


def test_outlier_flags_require_three_amounts_and_use_two_z_threshold() -> None:
    cells = [AnalysisCell("18.01", "Cooktop", "cooktop")]
    statuses = [
        _status("quote-a", "18.01", "included", amount_cents=100),
        _status("quote-b", "18.01", "included", amount_cents=100),
        _status("quote-c", "18.01", "included", amount_cents=100),
        _status("quote-d", "18.01", "included", amount_cents=100),
        _status("quote-e", "18.01", "included", amount_cents=400),
    ]

    flags = generate_analysis_flags(
        context=_context(),
        quotes=[AnalysisQuote(status.quote_id, status.quote_id, 1_000_000) for status in statuses],
        cells=cells,
        statuses=statuses,
        benchmarks=[],
    )

    outliers = [flag for flag in flags if flag.flag_type == "price_outlier"]
    assert len(outliers) == 1
    assert outliers[0].quote_id == "quote-e"
    assert outliers[0].severity == "info"
    assert outliers[0].evidence["z_score"] == 2.0

    no_outliers = generate_analysis_flags(
        context=_context(),
        quotes=[AnalysisQuote("quote-a", "A", 1_000_000), AnalysisQuote("quote-b", "B", 1_000_000)],
        cells=cells,
        statuses=statuses[:2],
        benchmarks=[],
    )
    assert [flag for flag in no_outliers if flag.flag_type == "price_outlier"] == []


def test_gap_matrix_is_per_cell_by_quote_status_grid() -> None:
    matrix = build_gap_matrix(
        quotes=[
            AnalysisQuote("quote-a", "A Homes", 1_000_000),
            AnalysisQuote("quote-b", "B Homes", 1_100_000),
        ],
        cells=[
            AnalysisCell("01.01", "Approval", "approval"),
            AnalysisCell("18.01", "Cooktop", "cooktop"),
        ],
        statuses=[
            _status("quote-a", "01.01", "included", amount_cents=200_000, qa_state="auto_pass"),
            _status("quote-b", "18.01", "silent_ambiguous"),
        ],
    )

    assert matrix == [
        {
            "cell_code": "01.01",
            "cell_name": "Approval",
            "quotes": [
                {
                    "status": "included",
                    "amount_cents": 200_000,
                    "bundled_into_cell": None,
                    "qa_state": "auto_pass",
                    "confidence": None,
                },
                {
                    "status": None,
                    "amount_cents": None,
                    "qa_state": None,
                    "confidence": None,
                },
            ],
        },
        {
            "cell_code": "18.01",
            "cell_name": "Cooktop",
            "quotes": [
                {
                    "status": None,
                    "amount_cents": None,
                    "qa_state": None,
                    "confidence": None,
                },
                {
                    "status": "silent_ambiguous",
                    "amount_cents": None,
                    "bundled_into_cell": None,
                    "qa_state": "needs_review",
                    "confidence": None,
                },
            ],
        },
    ]


def test_flag_merge_preserves_confirmed_and_suppressed_by_identity() -> None:
    confirmed = _flag("gap", qa_state="confirmed")
    suppressed = _flag("price_outlier", qa_state="suppressed")
    stale = _flag("scope_ambiguity")
    replacement_gap = _flag("gap", severity="warning")
    fresh = _flag("low_pc_allowance")

    merge = merge_generated_flags(
        existing=[confirmed, suppressed, stale],
        drafts=[replacement_gap, fresh],
    )

    assert merge.preserved == (confirmed, suppressed)
    assert merge.deleted == (stale,)
    assert merge.inserted == (fresh,)
    assert merge.current == (confirmed, suppressed, fresh)


def _status(
    quote_id: str,
    cell_code: str,
    status: str,
    *,
    amount_cents: int | None = None,
    qa_state: str = "needs_review",
) -> AnalysisCellStatus:
    return AnalysisCellStatus(
        comparison_id="comparison",
        quote_id=quote_id,
        cell_code=cell_code,
        status=status,
        amount_cents=amount_cents,
        qa_state=qa_state,
    )


def _flag(
    flag_type: str,
    *,
    severity: str = "caution",
    qa_state: str = "needs_review",
) -> AnalysisFlagDraft:
    return AnalysisFlagDraft(
        comparison_id="comparison",
        quote_id="quote-a",
        cell_code="18.01",
        flag_type=flag_type,
        severity=severity,
        headline_key=f"flag_phrases.{flag_type}",
        detail_key=None,
        evidence={},
        qa_state=qa_state,
    )


def _benchmark(
    key: str,
    *,
    confidence: str,
    p25: int,
    p50: int,
    p75: int,
) -> BenchmarkRow:
    return BenchmarkRow(
        id=key,
        benchmark_key=key,
        state="NSW",
        region="metro",
        build_type="new_build",
        spec_level="mid",
        metric="absolute",
        p25=Decimal(p25),
        p50=Decimal(p50),
        p75=Decimal(p75),
        unit="AUD",
        source="model_seed",
        provenance="fixture",
        confidence=confidence,
        effective_date=date(2026, 1, 1),
    )


def _context() -> ProjectContext:
    return ProjectContext.model_validate(
        {
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
    )
