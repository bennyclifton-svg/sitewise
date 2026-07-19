from __future__ import annotations

from typing import Any

from tender import worker
from tender.schemas import ProjectContext
from tender.services import mapping
from tests.conftest import run_async


def test_map_line_item_cascade_accepts_t0_before_other_tiers() -> None:
    calls: list[str] = []

    async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
        calls.append(f"t0:{phrase_norm}")
        return [mapping.CellCandidate("03.05", 1.0, "exact")]

    decision = run_async(
        mapping.map_line_item_cascade(
            object(),
            _item("Retaining Walls"),
            context=_context(),
            llm_client=object(),
            t0_func=t0,
            t1_func=_unexpected_t1,
            cell_loader=_unexpected_cell_loader,
            active_cell_loader=_unexpected_active_loader,
        )
    )

    assert calls == ["t0:retaining walls"]
    assert decision.tier == "t0_exact"
    assert decision.allocations == (mapping.CellAllocation("03.05", 1.0),)
    assert decision.qa_state == "auto_pass"


def test_map_line_item_cascade_accepts_t1_margin_hit() -> None:
    async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
        return []

    async def t1(session: Any, embedding: list[float], limit: int = 5) -> list[mapping.CellCandidate]:
        return [
            mapping.CellCandidate("03.05", 0.84, "retaining"),
            mapping.CellCandidate("03.01", 0.70, "site costs"),
        ]

    decision = run_async(
        mapping.map_line_item_cascade(
            object(),
            _item("Retaining", embedding=[1.0, 0.0, 0.0]),
            context=_context(),
            llm_client=object(),
            t0_func=t0,
            t1_func=t1,
            cell_loader=_unexpected_cell_loader,
            active_cell_loader=_unexpected_active_loader,
        )
    )

    assert decision.tier == "t1_embedding"
    assert decision.confidence == 0.84
    assert decision.qa_state == "auto_pass"


def test_map_line_item_cascade_uses_t2_when_t1_not_accepted() -> None:
    async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
        return []

    async def t1(session: Any, embedding: list[float], limit: int = 5) -> list[mapping.CellCandidate]:
        return [
            mapping.CellCandidate("03.05", 0.82, "retaining"),
            mapping.CellCandidate("03.01", 0.77, "site costs"),
        ]

    async def t2(**kwargs: Any) -> mapping.MappingDecision:
        return mapping.MappingDecision(
            tier="t2_small_llm",
            allocations=(mapping.CellAllocation("03.05", 1.0),),
            confidence=0.88,
            qa_state="auto_pass",
            adjudication={"rationale": "t2"},
        )

    decision = run_async(
        mapping.map_line_item_cascade(
            object(),
            _item("Retaining", embedding=[1.0, 0.0, 0.0]),
            context=_context(),
            llm_client=object(),
            t0_func=t0,
            t1_func=t1,
            t2_func=t2,
            cell_loader=_cell_loader,
            active_cell_loader=_unexpected_active_loader,
        )
    )

    assert decision.tier == "t2_small_llm"
    assert decision.adjudication["rationale"] == "t2"


def test_map_line_item_cascade_escalates_only_none_of_these_to_t3() -> None:
    async def t0(session: Any, phrase_norm: str) -> list[mapping.CellCandidate]:
        return []

    async def t1(session: Any, embedding: list[float], limit: int = 5) -> list[mapping.CellCandidate]:
        return [mapping.CellCandidate("03.05", 0.70, "retaining")]

    async def t2(**kwargs: Any) -> mapping.MappingDecision:
        return mapping.MappingDecision(
            tier="t2_small_llm",
            allocations=(),
            confidence=0.91,
            qa_state="needs_review",
            adjudication={"rationale": "none"},
            escalate_to_t3=True,
        )

    async def t3(**kwargs: Any) -> mapping.MappingDecision:
        return mapping.MappingDecision(
            tier="t3_frontier",
            allocations=(mapping.CellAllocation("19.01", 1.0),),
            confidence=0.82,
            qa_state="auto_pass",
            adjudication={"rationale": "t3"},
        )

    decision = run_async(
        mapping.map_line_item_cascade(
            object(),
            _item("Driveway", embedding=[1.0, 0.0, 0.0]),
            context=_context(),
            llm_client=object(),
            t0_func=t0,
            t1_func=t1,
            t2_func=t2,
            t3_func=t3,
            cell_loader=_cell_loader,
            active_cell_loader=_active_cell_loader,
        )
    )

    assert decision.tier == "t3_frontier"
    assert decision.allocations == (mapping.CellAllocation("19.01", 1.0),)


def test_map_items_skips_duplicate_line_items(monkeypatch: Any) -> None:
    """I3: reprint duplicates are not mapped; originals still are."""
    import uuid
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from tender.models import TenderJob

    quote_id = uuid.uuid4()
    original = SimpleNamespace(
        id=uuid.uuid4(),
        quote_id=quote_id,
        description_raw="Joinery",
        section_path=("Interior",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
        embedding=None,
        duplicate_of_id=None,
        created_at=None,
    )
    reprint = SimpleNamespace(
        id=uuid.uuid4(),
        quote_id=quote_id,
        description_raw="Joinery reprint",
        section_path=("Summary",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
        embedding=None,
        duplicate_of_id=original.id,
        created_at=None,
    )
    mapped: list[str] = []

    async def free_tier(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        mapped.append(item.description_raw)
        return mapping.FreeTierResult(
            decision=mapping.MappingDecision(
                tier="t0_exact",
                allocations=(mapping.CellAllocation("13.01", 1.0),),
                confidence=1.0,
                qa_state="auto_pass",
                adjudication={},
            )
        )

    monkeypatch.setattr(
        mapping, "_context_for_quote", AsyncMock(return_value=_context())
    )
    monkeypatch.setattr(mapping, "_existing_mappings", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        mapping,
        "load_active_cell_summaries",
        AsyncMock(return_value=[mapping.TaxonomyCellSummary("13.01", "Joinery")]),
    )
    monkeypatch.setattr(mapping, "resolve_free_tier", free_tier)
    monkeypatch.setattr(mapping, "_add_mapping_rows", lambda *a, **k: None)
    monkeypatch.setattr(mapping, "_sweep_unmapped", AsyncMock())

    class _Result:
        def scalars(self):
            return iter([original, reprint])

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_Result())
    session.get = AsyncMock(
        return_value=SimpleNamespace(stage="map_items", comparison_id=uuid.uuid4())
    )
    session.flush = AsyncMock()

    class _SessionCM:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    run_async(
        mapping.map_items(
            session,
            TenderJob(
                kind="map_items",
                comparison_id=uuid.uuid4(),
                quote_id=quote_id,
                payload={},
            ),
            session_factory=lambda: _SessionCM(),
            concurrency=2,
        )
    )

    assert mapped == ["Joinery"]


def test_mapping_protection_skips_human_confirmed_or_corrected_rows() -> None:
    assert mapping.has_protected_mapping([_mapping("human", "needs_review")])
    assert mapping.has_protected_mapping([_mapping("t1_embedding", "confirmed")])
    assert mapping.has_protected_mapping([_mapping("t1_embedding", "corrected")])
    assert not mapping.has_protected_mapping([_mapping("t1_embedding", "auto_pass")])


def test_worker_registers_map_items_handler() -> None:
    assert worker.HANDLERS["map_items"] is mapping.map_items


async def _cell_loader(
    session: Any, codes: list[str]
) -> list[mapping.TaxonomyCellSummary]:
    return [mapping.TaxonomyCellSummary(code, f"Cell {code}") for code in codes]


async def _active_cell_loader(session: Any) -> list[mapping.TaxonomyCellSummary]:
    return [mapping.TaxonomyCellSummary("19.01", "Driveway")]


async def _unexpected_t1(
    session: Any, embedding: list[float], limit: int = 5
) -> list[mapping.CellCandidate]:
    raise AssertionError("T1 should not be called")


async def _unexpected_cell_loader(
    session: Any, codes: list[str]
) -> list[mapping.TaxonomyCellSummary]:
    raise AssertionError("cell loader should not be called")


async def _unexpected_active_loader(session: Any) -> list[mapping.TaxonomyCellSummary]:
    raise AssertionError("active cell loader should not be called")


def _mapping(tier: str, qa_state: str) -> object:
    return type("ExistingMapping", (), {"tier": tier, "qa_state": qa_state})()


def _item(description: str, embedding: list[float] | None = None) -> mapping.LineItemMappingInput:
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
