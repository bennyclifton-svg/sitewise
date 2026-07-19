from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from tender.models import UNALLOCATED_TRADE_CODE
from tender.services import mapping
from tests.conftest import run_async


def test_t0_match_returns_exact_single_cell() -> None:
    session = FakeSession([row(cell_code="03.05", phrase="retaining walls")])

    result = run_async(mapping.t0_match(session, "retaining walls"))

    assert result == [
        mapping.CellCandidate(cell_code="03.05", similarity=1.0, via="exact")
    ]
    assert len(session.statements) == 1


def test_t0_match_uses_trigram_when_exact_misses() -> None:
    session = FakeSession(
        [],
        [row(cell_code="03.05", phrase="retaining wall", similarity=0.94)],
    )

    result = run_async(mapping.t0_match(session, "retaning wall"))

    assert result == [
        mapping.CellCandidate(cell_code="03.05", similarity=0.94, via="retaining wall")
    ]
    assert len(session.statements) == 2


def test_t0_match_returns_empty_for_multi_cell_exact_ambiguity() -> None:
    session = FakeSession(
        [
            row(cell_code="03.01", phrase="site costs"),
            row(cell_code="20.01", phrase="site costs"),
        ]
    )

    assert run_async(mapping.t0_match(session, "site costs")) == []


def test_t1_candidates_aggregate_by_max_similarity_and_order() -> None:
    session = FakeSession(
        [
            row(cell_code="03.01", phrase="site costs", similarity=0.81),
            row(cell_code="03.05", phrase="retaining", similarity=0.93),
            row(cell_code="03.05", phrase="retaining wall", similarity=0.91),
            row(cell_code="19.01", phrase="driveway", similarity=0.78),
        ]
    )

    result = run_async(mapping.t1_candidates(session, [1.0, 0.0, 0.0], limit=2))

    assert result == [
        mapping.CellCandidate(cell_code="03.05", similarity=0.93, via="retaining"),
        mapping.CellCandidate(cell_code="03.01", similarity=0.81, via="site costs"),
    ]


def test_t1_accept_candidate_requires_similarity_and_margin() -> None:
    confident = [
        mapping.CellCandidate(cell_code="03.05", similarity=0.83, via="retaining"),
        mapping.CellCandidate(cell_code="03.01", similarity=0.70, via="site costs"),
    ]
    low_margin = [
        mapping.CellCandidate(cell_code="03.05", similarity=0.83, via="retaining"),
        mapping.CellCandidate(cell_code="03.01", similarity=0.76, via="site costs"),
    ]
    low_similarity = [
        mapping.CellCandidate(cell_code="03.05", similarity=0.79, via="retaining")
    ]

    assert mapping.accept_t1_candidate(confident) == confident[0]
    assert mapping.accept_t1_candidate(low_margin) is None
    assert mapping.accept_t1_candidate(low_similarity) is None


def test_t0_seed_match_direct_figure_key() -> None:
    quote_id = uuid.uuid4()
    item = mapping.LineItemMappingInput(
        description_raw="Joinery package",
        section_path=("Interior",),
        qty=None,
        unit=None,
        amount_cents=100_000,
        item_status="included",
        figure_key="p10-1",
        counted_in_total=True,
    )
    seed_index = {"p10-1": "PT.01"}

    result = mapping.t0_seed_match(
        item,
        seed_index=seed_index,
        figure_key_by_id={},
        parent_by_id={},
    )

    assert result == [
        mapping.CellCandidate(cell_code="PT.01", similarity=1.0, via="seed:p10-1")
    ]
    assert mapping.build_seed_index(
        [
            mapping.ProjectTradeInfo(
                id=uuid.uuid4(),
                code="PT.01",
                name="Joinery",
                seed_assignments=(
                    {"quote_id": str(quote_id), "figure_key": "p10-1"},
                ),
            )
        ],
        quote_id,
    ) == {"p10-1": "PT.01"}


def test_t0_seed_match_via_ancestor_figure_key() -> None:
    parent_id = uuid.uuid4()
    item = mapping.LineItemMappingInput(
        description_raw="Kitchen cabinets",
        section_path=("Interior", "Joinery"),
        qty=None,
        unit=None,
        amount_cents=50_000,
        item_status="included",
        figure_key="p10-3",
        parent_id=parent_id,
    )

    result = mapping.t0_seed_match(
        item,
        seed_index={"p10-1": "PT.01"},
        figure_key_by_id={parent_id: "p10-1"},
        parent_by_id={parent_id: None},
    )

    assert result == [
        mapping.CellCandidate(cell_code="PT.01", similarity=1.0, via="seed:p10-1")
    ]


def test_t1_trade_candidates_excludes_unalloc_and_ranks() -> None:
    trades = [
        mapping.ProjectTradeInfo(
            id=uuid.uuid4(),
            code="PT.01",
            name="Joinery",
            embedding=[1.0, 0.0, 0.0],
        ),
        mapping.ProjectTradeInfo(
            id=uuid.uuid4(),
            code="PT.02",
            name="Site",
            embedding=[0.0, 1.0, 0.0],
        ),
        mapping.ProjectTradeInfo(
            id=uuid.uuid4(),
            code=UNALLOCATED_TRADE_CODE,
            name="Unallocated",
            embedding=[1.0, 0.0, 0.0],
        ),
    ]

    result = mapping.t1_trade_candidates([1.0, 0.0, 0.0], trades, limit=5)

    assert [candidate.cell_code for candidate in result] == ["PT.01", "PT.02"]
    assert result[0].similarity == 1.0
    assert UNALLOCATED_TRADE_CODE not in {c.cell_code for c in result}


def test_taxonomy_seed_tier_on_seed_hit() -> None:
    free = mapping.resolve_free_tier_trades(
        mapping.LineItemMappingInput(
            description_raw="Joinery",
            section_path=("Interior",),
            qty=None,
            unit=None,
            amount_cents=10_000,
            item_status="included",
            figure_key="p1-1",
        ),
        seed_index={"p1-1": "PT.01"},
        trades=[
            mapping.ProjectTradeInfo(
                id=uuid.uuid4(), code="PT.01", name="Joinery"
            )
        ],
        figure_key_by_id={},
        parent_by_id={},
    )

    assert free.decision is not None
    assert free.decision.tier == "taxonomy_seed"
    assert free.decision.qa_state == "auto_pass"
    assert free.decision.allocations == (mapping.CellAllocation("PT.01", 1.0),)


class FakeSession:
    def __init__(self, *results: list[SimpleNamespace]) -> None:
        self.results = list(results)
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> "FakeResult":
        self.statements.append(statement)
        return FakeResult(self.results.pop(0))


class FakeResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self.rows


def row(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)
