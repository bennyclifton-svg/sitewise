from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from tender.schemas import ProjectContext
from tender.services import expectations
from tender.services.analysis import (
    AnalysisCell,
    AnalysisCellStatus,
    AnalysisQuote,
    analysis_result_to_json,
    analyse_comparison,
    generate_analysis_flags,
)
from tender.services.benchmarks import BenchmarkRow


def test_synthetic_expectations_silence_analysis_fixture_matches_expected_json() -> None:
    comparison_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    quote_a = uuid.UUID("00000000-0000-0000-0000-000000000101")
    quote_b = uuid.UUID("00000000-0000-0000-0000-000000000102")
    line_item_id = uuid.UUID("00000000-0000-0000-0000-000000000201")

    drafts = expectations.build_cell_status_grid(
        comparison_id=comparison_id,
        quote_ids=[quote_a, quote_b],
        fired_rules=[
            expectations.FiredRule("APPROVAL.MUST", "01.01", "must", None),
            expectations.FiredRule("COOKTOP.MUST", "18.01", "must", None),
        ],
        mapped_items=[
            expectations.MappedCellItem(
                line_item_id=line_item_id,
                quote_id=quote_b,
                cell_code="18.01",
                item_status="pc_allowance",
                allowance_cents=200_000,
            )
        ],
    )
    statuses = _fake_silence_outcomes(drafts)
    quotes = [
        AnalysisQuote(str(quote_a), "A Homes", 1_000_000),
        AnalysisQuote(str(quote_b), "B Homes", 900_000),
    ]
    cells = [
        AnalysisCell("01.01", "Approval", "approval"),
        AnalysisCell("18.01", "Cooktop", "cooktop"),
    ]
    benchmarks = [
        _benchmark("approval", p25=75_000, p50=100_000, p75=150_000),
        _benchmark("cooktop", p25=300_000, p50=500_000, p75=700_000),
    ]

    result = analyse_comparison(
        context=_context(),
        quotes=quotes,
        cells=cells,
        statuses=statuses,
        benchmarks=benchmarks,
    )
    flags = generate_analysis_flags(
        context=_context(),
        quotes=quotes,
        cells=cells,
        statuses=statuses,
        benchmarks=benchmarks,
    )
    actual = analysis_result_to_json(result)
    actual["flag_summary"] = [
        [flag.flag_type, flag.quote_id, flag.cell_code, flag.severity] for flag in flags
    ]

    expected_path = Path(__file__).with_name("fixtures") / "analysis_expected.json"
    assert actual == json.loads(expected_path.read_text(encoding="utf-8"))


def _fake_silence_outcomes(
    drafts: list[expectations.CellStatusDraft],
) -> list[AnalysisCellStatus]:
    rows: list[AnalysisCellStatus] = []
    for draft in drafts:
        status = draft.status
        amount_cents = draft.amount_cents
        bundled_into_cell = draft.bundled_into_cell
        evidence = draft.evidence
        qa_state = draft.qa_state
        if str(draft.quote_id).endswith("101") and draft.cell_code == "01.01":
            status = "excluded_explicit"
            evidence = {"page_refs": [{"doc": "quote-a", "page": 2}]}
        if str(draft.quote_id).endswith("101") and draft.cell_code == "18.01":
            status = "silent_ambiguous"
            qa_state = "confirmed"
            evidence = {}
        if str(draft.quote_id).endswith("102") and draft.cell_code == "01.01":
            status = "bundled"
            bundled_into_cell = "01.07"
        rows.append(
            AnalysisCellStatus(
                comparison_id=str(draft.comparison_id),
                quote_id=str(draft.quote_id),
                cell_code=draft.cell_code,
                status=status,
                amount_cents=amount_cents,
                bundled_into_cell=bundled_into_cell,
                evidence=evidence,
                confidence=draft.confidence,
                qa_state=qa_state,
            )
        )
    return rows


def _benchmark(key: str, *, p25: int, p50: int, p75: int) -> BenchmarkRow:
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
        confidence="high",
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
