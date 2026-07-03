from __future__ import annotations

from typing import Any

from tender.llm.client import LLMAdjudicationResponse
from tender.schemas import ProjectContext
from tender.services import mapping
from tests.conftest import run_async


def test_t2_adjudication_uses_stable_candidate_choices() -> None:
    llm = FakeAdjudicator(
        LLMAdjudicationResponse(
            choice="03.05",
            confidence=0.86,
            rationale="retaining scope",
            model="gpt-small-test",
            prompt_version=mapping.T2_PROMPT_VERSION,
            request_id="req-t2",
        )
    )

    decision = run_async(
        mapping.t2_map_item(
            _item("Retaining wall allowance"),
            candidates=[
                mapping.CellCandidate("03.05", 0.78, "retaining"),
                mapping.CellCandidate("03.01", 0.72, "site costs"),
            ],
            candidate_cells=[
                mapping.TaxonomyCellSummary("03.01", "Site costs", "Site works", 1),
                mapping.TaxonomyCellSummary("03.05", "Retaining walls", "Walls", 2),
            ],
            context=_context(),
            llm_client=llm,
        )
    )

    assert llm.calls[0]["choices"] == ["03.05", "03.01", "none_of_these"]
    assert llm.calls[0]["model_key"] == "tender_model_adjudicate_small"
    assert llm.calls[0]["evidence"]["taxonomy_block"] == (
        "03.05 | Retaining walls | Walls\n03.01 | Site costs | Site works"
    )
    assert decision.allocations == (mapping.CellAllocation("03.05", 1.0),)
    assert decision.qa_state == "auto_pass"
    assert decision.adjudication["request_id"] == "req-t2"


def test_t2_low_confidence_marks_review_without_t3_escalation() -> None:
    llm = FakeAdjudicator(
        LLMAdjudicationResponse(
            choice="03.05",
            confidence=0.79,
            rationale="close but weak",
            model="gpt-small-test",
            prompt_version=mapping.T2_PROMPT_VERSION,
        )
    )

    decision = run_async(
        mapping.t2_map_item(
            _item("Retaining"),
            candidates=[mapping.CellCandidate("03.05", 0.72, "retaining")],
            candidate_cells=[mapping.TaxonomyCellSummary("03.05", "Retaining walls")],
            context=_context(),
            llm_client=llm,
        )
    )

    assert decision.allocations == (mapping.CellAllocation("03.05", 1.0),)
    assert decision.qa_state == "needs_review"


def test_t2_none_of_these_returns_escalation_decision() -> None:
    llm = FakeAdjudicator(
        LLMAdjudicationResponse(
            choice="none_of_these",
            confidence=0.91,
            rationale="not represented",
            model="gpt-small-test",
            prompt_version=mapping.T2_PROMPT_VERSION,
        )
    )

    decision = run_async(
        mapping.t2_map_item(
            _item("Pool equipment"),
            candidates=[mapping.CellCandidate("03.05", 0.72, "retaining")],
            candidate_cells=[mapping.TaxonomyCellSummary("03.05", "Retaining walls")],
            context=_context(),
            llm_client=llm,
        )
    )

    assert decision.allocations == ()
    assert decision.escalate_to_t3 is True


def test_t3_normalizes_positive_split_fractions() -> None:
    frontier = FakeFrontierMapper(
        mapping.FrontierMappingResponse(
            allocations=(
                mapping.CellAllocation("03.05", 2.0),
                mapping.CellAllocation("19.01", 1.0),
            ),
            confidence=0.82,
            rationale="split scope",
            model="gpt-frontier-test",
            prompt_version=mapping.T3_PROMPT_VERSION,
            request_id="req-t3",
        )
    )

    decision = run_async(
        mapping.t3_map_item(
            _item("Retaining wall and driveway works"),
            active_cells=[
                mapping.TaxonomyCellSummary("19.01", "Driveway", sort_order=3),
                mapping.TaxonomyCellSummary("03.05", "Retaining walls", sort_order=2),
            ],
            context=_context(),
            frontier_client=frontier,
        )
    )

    assert frontier.calls[0]["cell_codes"] == ["03.05", "19.01"]
    assert decision.allocations == (
        mapping.CellAllocation("03.05", 2 / 3),
        mapping.CellAllocation("19.01", 1 / 3),
    )
    assert decision.qa_state == "auto_pass"


def test_t3_unknown_cell_code_needs_review_without_invented_row() -> None:
    frontier = FakeFrontierMapper(
        mapping.FrontierMappingResponse(
            allocations=(mapping.CellAllocation("99.99", 1.0),),
            confidence=0.95,
            rationale="unknown",
            model="gpt-frontier-test",
            prompt_version=mapping.T3_PROMPT_VERSION,
            raw={"mappings": [{"cell_code": "99.99", "allocation_fraction": 1.0}]},
        )
    )

    decision = run_async(
        mapping.t3_map_item(
            _item("Mystery line"),
            active_cells=[mapping.TaxonomyCellSummary("03.05", "Retaining walls")],
            context=_context(),
            frontier_client=frontier,
        )
    )

    assert decision.allocations == ()
    assert decision.qa_state == "needs_review"
    assert decision.adjudication["error"] == "unknown_cell_code"
    assert decision.adjudication["raw_response"]["mappings"][0]["cell_code"] == "99.99"


def test_t3_rejects_empty_active_taxonomy() -> None:
    frontier = FakeFrontierMapper(
        mapping.FrontierMappingResponse(
            allocations=(mapping.CellAllocation("03.05", 1.0),),
            confidence=0.9,
            rationale="unused",
            model="gpt-frontier-test",
            prompt_version=mapping.T3_PROMPT_VERSION,
        )
    )

    async def _run() -> None:
        try:
            await mapping.t3_map_item(
                _item("Retaining wall"),
                active_cells=[],
                context=_context(),
                frontier_client=frontier,
            )
        except ValueError as exc:
            assert str(exc) == "tender taxonomy seed data has no active cells"
        else:
            raise AssertionError("expected empty taxonomy to fail")

    run_async(_run())
    assert frontier.calls == []


class FakeAdjudicator:
    def __init__(self, response: LLMAdjudicationResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def adjudicate(
        self,
        question: str,
        choices: list[str],
        evidence: dict[str, Any],
        context: ProjectContext,
        *,
        prompt_version: str,
        model_key: str,
    ) -> LLMAdjudicationResponse:
        self.calls.append(
            {
                "question": question,
                "choices": choices,
                "evidence": evidence,
                "prompt_version": prompt_version,
                "model_key": model_key,
            }
        )
        return self.response


class FakeFrontierMapper:
    def __init__(self, response: mapping.FrontierMappingResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def map_item_open(
        self,
        *,
        line_item: dict[str, Any],
        active_cells: list[mapping.TaxonomyCellSummary],
        context: ProjectContext,
        prompt_version: str,
        model_key: str,
    ) -> mapping.FrontierMappingResponse:
        self.calls.append(
            {
                "line_item": line_item,
                "cell_codes": [cell.code for cell in active_cells],
                "prompt_version": prompt_version,
                "model_key": model_key,
            }
        )
        return self.response


def _item(description: str) -> mapping.LineItemMappingInput:
    return mapping.LineItemMappingInput(
        description_raw=description,
        section_path=("Site works",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
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
