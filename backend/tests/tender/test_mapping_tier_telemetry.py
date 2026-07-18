"""Packet A2: map cascade records per-tier counters into stage usage."""

from __future__ import annotations

from typing import Any

from tender.schemas import ProjectContext
from tender.services import mapping, telemetry
from tests.conftest import run_async


def test_map_line_item_cascade_records_t0_tier_stats() -> None:
    usage = telemetry.begin_stage_usage()
    try:

        async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
            return [mapping.CellCandidate("03.05", 1.0, "exact")]

        decision = run_async(
            mapping.map_line_item_cascade(
                object(),
                _item("Retaining Walls"),
                context=_context(),
                llm_client=object(),
                t0_func=t0,
                t1_func=_unexpected_t1,
                active_cell_loader=_unexpected_active_loader,
            )
        )
    finally:
        telemetry.end_stage_usage()

    assert decision.tier == "t0_exact"
    assert usage.metadata["tiers"]["t0"] == 1
    assert usage.metadata["tiers"]["t0_ms"] >= 0
    assert usage.metadata["tiers"]["t1"] == 0


def test_map_line_item_cascade_records_final_t3_after_escalation() -> None:
    usage = telemetry.begin_stage_usage()
    try:

        async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
            return []

        async def t1(
            session: Any, embedding: list[float], limit: int = 5
        ) -> list[mapping.CellCandidate]:
            return [mapping.CellCandidate("03.05", 0.70, "retaining")]

        async def t2(**kwargs: Any) -> mapping.MappingDecision:
            return mapping.MappingDecision(
                tier="t2_small_llm",
                allocations=(),
                confidence=0.91,
                qa_state="needs_review",
                adjudication={},
                escalate_to_t3=True,
            )

        async def t3(**kwargs: Any) -> mapping.MappingDecision:
            return mapping.MappingDecision(
                tier="t3_frontier",
                allocations=(mapping.CellAllocation("19.01", 1.0),),
                confidence=0.82,
                qa_state="auto_pass",
                adjudication={},
            )

        async def cell_loader(
            session: Any, codes: list[str]
        ) -> list[mapping.TaxonomyCellSummary]:
            return [mapping.TaxonomyCellSummary(code, f"Cell {code}") for code in codes]

        async def active_loader(session: Any) -> list[mapping.TaxonomyCellSummary]:
            return [mapping.TaxonomyCellSummary("19.01", "Driveway")]

        decision = run_async(
            mapping.map_line_item_cascade(
                object(),
                _item("Driveway", embedding=[1.0, 0.0]),
                context=_context(),
                llm_client=object(),
                t0_func=t0,
                t1_func=t1,
                t2_func=t2,
                t3_func=t3,
                cell_loader=cell_loader,
                active_cell_loader=active_loader,
            )
        )
    finally:
        telemetry.end_stage_usage()

    assert decision.tier == "t3_frontier"
    assert usage.metadata["tiers"]["t3"] == 1
    assert usage.metadata["tiers"]["t2"] == 0


async def _unexpected_t1(
    session: Any, embedding: list[float], limit: int = 5
) -> list[mapping.CellCandidate]:
    raise AssertionError("T1 should not be called")


async def _unexpected_active_loader(session: Any) -> list[mapping.TaxonomyCellSummary]:
    raise AssertionError("active cell loader should not be called")


def _item(
    description: str, embedding: list[float] | None = None
) -> mapping.LineItemMappingInput:
    return mapping.LineItemMappingInput(
        description_raw=description,
        section_path=("Site works",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
        embedding=embedding,
    )


def _context() -> ProjectContext:
    return ProjectContext.model_validate(
        {
            "state": "NSW",
            "region": "metro",
            "build_type": "new_build",
            "dwelling_class": "class_1a",
            "storeys": 1,
            "soil_class": "M",
            "slope_class": "flat",
            "bal_rating": "none",
            "spec_level": "builder_base",
        }
    )
