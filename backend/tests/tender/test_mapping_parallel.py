"""Packet A1: bounded concurrent free-tier resolution in map_items."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from tender.models import TenderJob
from tender.schemas import ProjectContext
from tender.services import mapping
from tests.conftest import run_async


def test_map_items_runs_free_tiers_with_bounded_concurrency(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    line_items = [_fake_line_item(f"Item {index}", quote_id=quote_id) for index in range(8)]
    in_flight = 0
    max_in_flight = 0
    mapped_descriptions: list[str] = []

    async def slow_free(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        mapped_descriptions.append(item.description_raw)
        return mapping.FreeTierResult(decision=_decision(item.description_raw))

    _patch_map_items_deps(monkeypatch, slow_free)

    run_async(
        mapping.map_items(
            _session(line_items),
            _job(quote_id),
            session_factory=_session_factory(),
            concurrency=3,
        )
    )

    assert max_in_flight > 1
    assert max_in_flight <= 3
    assert sorted(mapped_descriptions) == sorted(
        item.description_raw for item in line_items
    )


def test_map_items_parallel_outcomes_match_serial_order(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    line_items = [_fake_line_item(f"Item {index}", quote_id=quote_id) for index in range(5)]
    decisions_by_description: dict[str, mapping.MappingDecision] = {
        item.description_raw: _decision(item.description_raw, cell_code=f"0{index}.01")
        for index, item in enumerate(line_items, start=1)
    }
    written: list[tuple[uuid.UUID, mapping.MappingDecision]] = []

    async def free_tier(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        await asyncio.sleep(0.01 * (5 - int(item.description_raw.split()[-1])))
        return mapping.FreeTierResult(
            decision=decisions_by_description[item.description_raw]
        )

    def capture_rows(
        session: Any,
        line_item_id: uuid.UUID,
        decision: mapping.MappingDecision,
        **kwargs: Any,
    ) -> None:
        written.append((line_item_id, decision))

    _patch_map_items_deps(monkeypatch, free_tier)
    monkeypatch.setattr(mapping, "_add_mapping_rows", capture_rows)

    run_async(
        mapping.map_items(
            _session(line_items),
            _job(quote_id),
            session_factory=_session_factory(),
            concurrency=4,
        )
    )

    assert [line_item_id for line_item_id, _ in written] == [
        item.id for item in line_items
    ]
    assert [decision.allocations[0].cell_code for _, decision in written] == [
        f"0{index}.01" for index in range(1, 6)
    ]


def test_map_items_loads_active_cells_once(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    line_items = [_fake_line_item(f"Item {index}", quote_id=quote_id) for index in range(4)]
    active_loads = 0
    active_cells = [
        mapping.TaxonomyCellSummary("03.01", "Site"),
        mapping.TaxonomyCellSummary("19.01", "Driveway"),
    ]
    t3_calls = 0

    async def counting_load(session: Any) -> list[mapping.TaxonomyCellSummary]:
        nonlocal active_loads
        active_loads += 1
        return active_cells

    async def free_tier(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        return mapping.FreeTierResult()

    async def t3(
        item: mapping.LineItemMappingInput,
        *,
        active_cells: list[mapping.TaxonomyCellSummary],
        context: ProjectContext,
        frontier_client: Any = None,
        prompt_version: str = mapping.T3_PROMPT_VERSION,
    ) -> mapping.MappingDecision:
        nonlocal t3_calls
        t3_calls += 1
        assert [cell.code for cell in active_cells] == ["03.01", "19.01"]
        assert prompt_version == mapping.T3_PROMPT_VERSION
        return _decision(item.description_raw)

    _patch_map_items_deps(monkeypatch, free_tier)
    monkeypatch.setattr(mapping, "load_active_cell_summaries", counting_load)
    monkeypatch.setattr(mapping, "t3_map_item", t3)

    run_async(
        mapping.map_items(
            _session(line_items),
            _job(quote_id),
            session_factory=_session_factory(),
            concurrency=4,
        )
    )

    assert active_loads == 1
    assert t3_calls == 4


def test_map_items_skips_protected_mappings(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    protected = _fake_line_item("Protected", quote_id=quote_id)
    open_item = _fake_line_item("Open", quote_id=quote_id)
    mapped: list[str] = []

    async def free_tier(
        session: Any,
        item: mapping.LineItemMappingInput,
        **kwargs: Any,
    ) -> mapping.FreeTierResult:
        mapped.append(item.description_raw)
        return mapping.FreeTierResult(decision=_decision(item.description_raw))

    async def existing_mappings(session: Any, line_item_id: uuid.UUID) -> list[Any]:
        if line_item_id == protected.id:
            return [SimpleNamespace(tier="human", qa_state="confirmed")]
        return []

    _patch_map_items_deps(monkeypatch, free_tier)
    monkeypatch.setattr(mapping, "_existing_mappings", existing_mappings)

    run_async(
        mapping.map_items(
            _session([protected, open_item]),
            _job(quote_id),
            session_factory=_session_factory(),
            concurrency=4,
        )
    )

    assert mapped == ["Open"]


def _patch_map_items_deps(monkeypatch: Any, free_tier: Any) -> None:
    monkeypatch.setattr(
        mapping,
        "_context_for_quote",
        AsyncMock(return_value=_context()),
    )
    monkeypatch.setattr(mapping, "_existing_mappings", AsyncMock(return_value=[]))
    monkeypatch.setattr(mapping, "load_project_trades", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        mapping,
        "load_active_cell_summaries",
        AsyncMock(return_value=[mapping.TaxonomyCellSummary("19.01", "Driveway")]),
    )
    monkeypatch.setattr(mapping, "resolve_free_tier", free_tier)
    monkeypatch.setattr(mapping, "_add_mapping_rows", lambda *args, **kwargs: None)


def _session(line_items: list[Any]) -> AsyncMock:
    quote = SimpleNamespace(stage="map_items", comparison_id=uuid.uuid4())

    class _Result:
        def scalars(self):
            return iter(line_items)

        def all(self):
            # Sweep query: nothing left unmapped in these unit fakes.
            return []

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


def _fake_line_item(
    description: str, *, quote_id: uuid.UUID | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        quote_id=quote_id or uuid.uuid4(),
        description_raw=description,
        section_path=("Site works",),
        qty=None,
        unit=None,
        amount_cents=100000,
        item_status="included",
        embedding=None,
        duplicate_of_id=None,
        figure_key=None,
        parent_id=None,
        counted_in_total=False,
        created_at=None,
    )


def _decision(
    description: str, *, cell_code: str = "19.01"
) -> mapping.MappingDecision:
    return mapping.MappingDecision(
        tier="t0_exact",
        allocations=(mapping.CellAllocation(cell_code, 1.0),),
        confidence=1.0,
        qa_state="auto_pass",
        adjudication={"via": description},
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
