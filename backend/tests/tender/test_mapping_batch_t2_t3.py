"""Packet A3: batch T2 via adjudicate_many + group-scoped T3."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from tender.llm.client import LLMAdjudicationResponse
from tender.models import TenderJob
from tender.schemas import ProjectContext
from tender.services import mapping
from tests.conftest import run_async


def test_taxonomy_group_from_cell_code() -> None:
    assert mapping.taxonomy_group("03.05") == "03"
    assert mapping.taxonomy_group("19.01") == "19"


def test_scope_cells_for_t3_keeps_candidate_groups_only() -> None:
    active = [
        mapping.TaxonomyCellSummary("03.01", "Site costs"),
        mapping.TaxonomyCellSummary("03.05", "Retaining walls"),
        mapping.TaxonomyCellSummary("19.01", "Driveway"),
        mapping.TaxonomyCellSummary("14.01", "Kitchen cabinets"),
    ]
    scoped = mapping.scope_cells_for_t3(
        active,
        t1_candidates=[
            mapping.CellCandidate("03.05", 0.7, "retaining"),
            mapping.CellCandidate("03.01", 0.65, "site"),
        ],
    )
    assert [cell.code for cell in scoped] == ["03.01", "03.05"]


def test_scope_cells_for_t3_falls_back_when_no_candidates() -> None:
    active = [
        mapping.TaxonomyCellSummary("03.01", "Site costs"),
        mapping.TaxonomyCellSummary("19.01", "Driveway"),
    ]
    scoped = mapping.scope_cells_for_t3(active, t1_candidates=[])
    assert [cell.code for cell in scoped] == ["03.01", "19.01"]


def test_t2_map_items_batch_uses_adjudicate_many_once() -> None:
    llm = FakeBatchAdjudicator(
        [
            LLMAdjudicationResponse(
                choice="03.05",
                confidence=0.9,
                rationale="retaining",
                model="gpt-small-test",
                prompt_version=mapping.T2_PROMPT_VERSION,
                request_id="batch-0",
            ),
            LLMAdjudicationResponse(
                choice="none_of_these",
                confidence=0.8,
                rationale="missing",
                model="gpt-small-test",
                prompt_version=mapping.T2_PROMPT_VERSION,
                request_id="batch-1",
            ),
        ]
    )
    decisions = run_async(
        mapping.t2_map_items_batch(
            [
                mapping.T2BatchItem(
                    item=_item("Retaining wall"),
                    candidates=(
                        mapping.CellCandidate("03.05", 0.78, "retaining"),
                        mapping.CellCandidate("03.01", 0.72, "site"),
                    ),
                    candidate_cells=(
                        mapping.TaxonomyCellSummary("03.05", "Retaining walls", "Walls"),
                        mapping.TaxonomyCellSummary("03.01", "Site costs", "Site"),
                    ),
                ),
                mapping.T2BatchItem(
                    item=_item("Pool equipment"),
                    candidates=(mapping.CellCandidate("03.05", 0.6, "retaining"),),
                    candidate_cells=(
                        mapping.TaxonomyCellSummary("03.05", "Retaining walls"),
                    ),
                ),
            ],
            context=_context(),
            llm_client=llm,
        )
    )

    assert llm.batch_calls == 1
    assert llm.single_calls == 0
    assert len(llm.evidence_items) == 2
    assert decisions[0].allocations == (mapping.CellAllocation("03.05", 1.0),)
    assert decisions[0].escalate_to_t3 is False
    assert decisions[1].escalate_to_t3 is True
    assert set(llm.choices) >= {"03.05", "03.01", "none_of_these"}


def test_t2_batch_rejects_choice_outside_item_candidates() -> None:
    llm = FakeBatchAdjudicator(
        [
            LLMAdjudicationResponse(
                choice="19.01",
                confidence=0.9,
                rationale="wrong item scope",
                model="gpt-small-test",
                prompt_version=mapping.T2_PROMPT_VERSION,
            )
        ]
    )
    decisions = run_async(
        mapping.t2_map_items_batch(
            [
                mapping.T2BatchItem(
                    item=_item("Retaining"),
                    candidates=(mapping.CellCandidate("03.05", 0.7, "retaining"),),
                    candidate_cells=(
                        mapping.TaxonomyCellSummary("03.05", "Retaining walls"),
                    ),
                )
            ],
            context=_context(),
            llm_client=llm,
        )
    )
    assert decisions[0].escalate_to_t3 is True
    assert decisions[0].allocations == ()


def test_map_line_item_cascade_scopes_t3_to_candidate_groups() -> None:
    seen_cells: list[str] = []

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
            confidence=0.9,
            qa_state="needs_review",
            adjudication={},
            escalate_to_t3=True,
        )

    async def t3(**kwargs: Any) -> mapping.MappingDecision:
        seen_cells.extend(cell.code for cell in kwargs["active_cells"])
        return mapping.MappingDecision(
            tier="t3_frontier",
            allocations=(mapping.CellAllocation("03.05", 1.0),),
            confidence=0.8,
            qa_state="auto_pass",
            adjudication={},
        )

    async def cell_loader(
        session: Any, codes: list[str]
    ) -> list[mapping.TaxonomyCellSummary]:
        return [mapping.TaxonomyCellSummary(code, f"Cell {code}") for code in codes]

    async def active_loader(session: Any) -> list[mapping.TaxonomyCellSummary]:
        return [
            mapping.TaxonomyCellSummary("03.01", "Site costs"),
            mapping.TaxonomyCellSummary("03.05", "Retaining walls"),
            mapping.TaxonomyCellSummary("19.01", "Driveway"),
        ]

    decision = run_async(
        mapping.map_line_item_cascade(
            object(),
            _item("Retaining", embedding=[1.0]),
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

    assert decision.tier == "t3_frontier"
    assert seen_cells == ["03.01", "03.05"]


def test_map_items_batches_t2_instead_of_per_item_adjudicate(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    line_items = [
        _fake_line_item("Retaining wall", quote_id=quote_id, embedding=[1.0, 0.0]),
        _fake_line_item("Site works PS", quote_id=quote_id, embedding=[0.0, 1.0]),
    ]
    batch_calls = 0

    async def free_tier(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        if item.description_raw.startswith("Retaining"):
            candidates = (
                mapping.CellCandidate("03.05", 0.75, "retaining"),
                mapping.CellCandidate("03.01", 0.70, "site"),
            )
        else:
            candidates = (
                mapping.CellCandidate("03.01", 0.74, "site"),
                mapping.CellCandidate("03.05", 0.70, "retaining"),
            )
        return mapping.FreeTierResult(
            t1_candidates=candidates,
            candidate_cells=tuple(
                mapping.TaxonomyCellSummary(c.cell_code, f"Cell {c.cell_code}")
                for c in candidates
            ),
        )

    async def batch_t2(
        items: Any,
        *,
        context: ProjectContext,
        llm_client: Any,
    ) -> list[mapping.MappingDecision]:
        nonlocal batch_calls
        batch_calls += 1
        assert len(items) == 2
        return [
            mapping.MappingDecision(
                tier="t2_small_llm",
                allocations=(mapping.CellAllocation("03.05", 1.0),),
                confidence=0.9,
                qa_state="auto_pass",
                adjudication={},
            ),
            mapping.MappingDecision(
                tier="t2_small_llm",
                allocations=(mapping.CellAllocation("03.01", 1.0),),
                confidence=0.88,
                qa_state="auto_pass",
                adjudication={},
            ),
        ]

    monkeypatch.setattr(mapping, "_context_for_quote", AsyncMock(return_value=_context()))
    monkeypatch.setattr(mapping, "_existing_mappings", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        mapping,
        "load_active_cell_summaries",
        AsyncMock(
            return_value=[
                mapping.TaxonomyCellSummary("03.01", "Site"),
                mapping.TaxonomyCellSummary("03.05", "Retaining"),
                mapping.TaxonomyCellSummary("19.01", "Driveway"),
            ]
        ),
    )
    monkeypatch.setattr(mapping, "resolve_free_tier", free_tier)
    monkeypatch.setattr(mapping, "t2_map_items_batch", batch_t2)
    monkeypatch.setattr(mapping, "_add_mapping_rows", lambda *a, **k: None)

    run_async(
        mapping.map_items(
            _session(line_items),
            _job(quote_id),
            session_factory=_session_factory(),
            concurrency=4,
            llm_client=object(),
        )
    )

    assert batch_calls == 1


class FakeBatchAdjudicator:
    def __init__(self, responses: list[LLMAdjudicationResponse]) -> None:
        self.responses = responses
        self.batch_calls = 0
        self.single_calls = 0
        self.evidence_items: list[dict[str, Any]] = []
        self.choices: list[str] = []

    async def adjudicate_many(
        self,
        question: str,
        choices: list[str],
        evidence_items: list[dict[str, Any]],
        context: ProjectContext,
        *,
        prompt_version: str,
        model_key: str,
    ) -> list[LLMAdjudicationResponse]:
        self.batch_calls += 1
        self.evidence_items = list(evidence_items)
        self.choices = list(choices)
        assert prompt_version == mapping.T2_PROMPT_VERSION
        assert model_key == "tender_model_adjudicate_small"
        assert "map one" in question.lower() or "taxonomy" in question.lower()
        return self.responses

    async def adjudicate(self, *args: Any, **kwargs: Any) -> LLMAdjudicationResponse:
        self.single_calls += 1
        raise AssertionError("single adjudicate should not be used for T2 batch")


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


def _fake_line_item(
    description: str,
    *,
    quote_id: uuid.UUID,
    embedding: list[float] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        quote_id=quote_id,
        description_raw=description,
        section_path=("Site works",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
        embedding=embedding,
    )


def _session(line_items: list[Any]) -> AsyncMock:
    quote = SimpleNamespace(stage="map_items", comparison_id=uuid.uuid4())

    class _Result:
        def scalars(self):
            return iter(line_items)

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_Result())
    session.get = AsyncMock(return_value=quote)
    session.flush = AsyncMock()
    return session


def _session_factory() -> Any:
    class _SessionCM:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    return lambda: _SessionCM()


def _job(quote_id: uuid.UUID) -> TenderJob:
    return TenderJob(
        kind="map_items",
        comparison_id=uuid.uuid4(),
        quote_id=quote_id,
        payload={},
    )
