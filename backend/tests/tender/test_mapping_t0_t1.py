from __future__ import annotations

from types import SimpleNamespace
from typing import Any

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
