"""Tests for project taxonomy generation (Task 4.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from tender.models import TenderJob, UNALLOCATED_TRADE_CODE
from tender.services import project_taxonomy
from tender.services.project_taxonomy import (
    CountedSection,
    alignment_hints,
    select_counted_sections,
)
from tests.conftest import run_async

Q1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
Q2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
COMPARISON_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _item(
    *,
    figure_key: str,
    description_raw: str,
    amount_ex_gst_cents: int | None,
    counted_in_total: bool = False,
    is_rollup: bool = False,
    parent_id: uuid.UUID | None = None,
    duplicate_of_id: uuid.UUID | None = None,
    item_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id or uuid.uuid4(),
        figure_key=figure_key,
        description_raw=description_raw,
        amount_ex_gst_cents=amount_ex_gst_cents,
        counted_in_total=counted_in_total,
        is_rollup=is_rollup,
        parent_id=parent_id,
        duplicate_of_id=duplicate_of_id,
        section_path=None,
    )


def test_select_counted_sections_prefers_counted_rollups() -> None:
    root = uuid.uuid4()
    items = [
        _item(
            figure_key="cat-a",
            description_raw="Cabinetry",
            amount_ex_gst_cents=360_300_00,
            counted_in_total=True,
            is_rollup=True,
            item_id=root,
        ),
        _item(
            figure_key="leaf-1",
            description_raw="Benchtops",
            amount_ex_gst_cents=45_000_00,
            counted_in_total=False,
            parent_id=root,
        ),
        _item(
            figure_key="cat-b",
            description_raw="Electrical",
            amount_ex_gst_cents=80_000_00,
            counted_in_total=True,
            is_rollup=True,
        ),
    ]

    sections = select_counted_sections(items)

    assert sections == [
        CountedSection("Cabinetry", 360_300_00, "cat-a"),
        CountedSection("Electrical", 80_000_00, "cat-b"),
    ]


def test_select_counted_sections_falls_back_to_children_when_no_rollups() -> None:
    """Montique shape: counted lump sum with PS children → use the PS groups."""
    lump_id = uuid.uuid4()
    items = [
        _item(
            figure_key="lump",
            description_raw="Contract sum",
            amount_ex_gst_cents=3_600_000_00,
            counted_in_total=True,
            is_rollup=False,
            item_id=lump_id,
        ),
        _item(
            figure_key="ps-cab",
            description_raw="PS: Cabinetry",
            amount_ex_gst_cents=120_000_00,
            counted_in_total=False,
            parent_id=lump_id,
        ),
        _item(
            figure_key="ps-elec",
            description_raw="PS: Electrical",
            amount_ex_gst_cents=40_000_00,
            counted_in_total=False,
            parent_id=lump_id,
        ),
    ]

    sections = select_counted_sections(items)

    assert [s.figure_key for s in sections] == ["ps-cab", "ps-elec"]
    assert [s.section_label for s in sections] == ["PS: Cabinetry", "PS: Electrical"]


def test_select_counted_sections_ignores_duplicates() -> None:
    items = [
        _item(
            figure_key="sec-1",
            description_raw="Joinery",
            amount_ex_gst_cents=100_00,
            counted_in_total=True,
            is_rollup=True,
        ),
        _item(
            figure_key="sec-1-dup",
            description_raw="Joinery (summary)",
            amount_ex_gst_cents=100_00,
            counted_in_total=True,
            is_rollup=True,
            duplicate_of_id=uuid.uuid4(),
        ),
    ]

    assert select_counted_sections(items) == [
        CountedSection("Joinery", 100_00, "sec-1"),
    ]


def test_alignment_hints_label_cosine() -> None:
    sections_by_quote = {
        Q1: [CountedSection("Cabinetry", 360_300_00, "q1-cab")],
        Q2: [CountedSection("Joinery / cabinetry", 327_000_00, "q2-join")],
    }
    # Near-identical vectors → cosine ≈ 1.0
    embeddings = {
        "Cabinetry": [1.0, 0.0, 0.0],
        "Joinery / cabinetry": [0.95, 0.3122, 0.0],  # cosine ≈ 0.95
    }

    hints = run_async(
        alignment_hints(sections_by_quote, label_embeddings=embeddings)
    )

    assert any(
        h.reason == "label_cosine"
        and set(h.left_figure_keys) | set(h.right_figure_keys)
        == {"q1-cab", "q2-join"}
        and h.score >= 0.75
        for h in hints
    )


def test_alignment_hints_amount_band_with_subset_sums() -> None:
    """Cabinetry ≈ Joinery + benchtops (2-element subset sum)."""
    sections_by_quote = {
        Q1: [CountedSection("Cabinetry", 400_000_00, "q1-cab")],
        Q2: [
            CountedSection("Joinery", 300_000_00, "q2-join"),
            CountedSection("Benchtops", 100_000_00, "q2-bench"),
            CountedSection("Roofing", 90_000_00, "q2-roof"),
        ],
    }

    hints = run_async(
        alignment_hints(sections_by_quote, label_embeddings={})
    )

    match = next(
        h
        for h in hints
        if h.reason == "amount_band"
        and set(h.left_figure_keys) | set(h.right_figure_keys)
        == {"q1-cab", "q2-join", "q2-bench"}
    )
    assert match.score <= 0.15


def test_alignment_hints_amount_band_single_pair() -> None:
    sections_by_quote = {
        Q1: [CountedSection("Electrical", 100_000_00, "q1-e")],
        Q2: [CountedSection("Electrical works", 110_000_00, "q2-e")],
    }
    # |100k-110k|/110k ≈ 0.0909 ≤ 0.15
    hints = run_async(
        alignment_hints(sections_by_quote, label_embeddings={})
    )
    assert any(h.reason == "amount_band" for h in hints)


def test_post_validate_drops_unknown_anchors_keeps_trade() -> None:
    sections_by_quote = {
        str(Q1): [CountedSection("Cabinetry", 100_00, "fk-1")],
    }
    drafts = project_taxonomy.post_validate_trades(
        [
            {
                "code": "PT.01",
                "name": "Cabinetry",
                "description": "Joinery package",
                "group_label": "Finishes",
                "sort_order": 1,
                "per_quote_sections": {str(Q1): ["fk-1"]},
                "anchor_cell_codes": ["18.01", "no.such"],
                "confidence": 0.9,
            }
        ],
        sections_by_quote=sections_by_quote,
        known_cell_codes={"18.01", "03.05"},
    )

    cabinetry = next(t for t in drafts if t.code == "PT.01")
    assert cabinetry.anchor_cell_codes == ["18.01"]
    assert any(t.code == UNALLOCATED_TRADE_CODE for t in drafts)


def test_post_validate_auto_trades_unassigned_sections() -> None:
    sections_by_quote = {
        str(Q1): [
            CountedSection("Cabinetry", 100_00, "fk-1"),
            CountedSection("Roofing", 50_00, "fk-2"),
        ],
    }
    drafts = project_taxonomy.post_validate_trades(
        [
            {
                "code": "PT.01",
                "name": "Cabinetry",
                "description": None,
                "group_label": None,
                "sort_order": 1,
                "per_quote_sections": {str(Q1): ["fk-1"]},
                "anchor_cell_codes": None,
                "confidence": 0.8,
            }
        ],
        sections_by_quote=sections_by_quote,
        known_cell_codes=set(),
    )

    codes = {t.code for t in drafts}
    assert "PT.01" in codes
    assert UNALLOCATED_TRADE_CODE in codes
    auto = next(t for t in drafts if t.code not in {"PT.01", UNALLOCATED_TRADE_CODE})
    assert auto.name == "Roofing"
    assert auto.seed_assignments == [
        {"quote_id": str(Q1), "figure_key": "fk-2"}
    ]


@dataclass
class FakeTaxonomyLLM:
    payload: dict[str, Any]
    calls: int = 0
    last_input: dict[str, Any] | None = None

    async def generate_project_taxonomy(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        self.last_input = kwargs
        return self.payload


@dataclass
class FakeEmbedder:
    vector: list[float] = field(default_factory=lambda: [0.1] * 8)

    async def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        return [list(self.vector) for _ in texts]


class FakeSession:
    """Minimal async session for generate_project_taxonomy orchestration tests."""

    def __init__(
        self,
        *,
        existing_trade_ids: list[uuid.UUID] | None = None,
        quote_ids: list[uuid.UUID] | None = None,
        line_items_by_quote: dict[uuid.UUID, list[SimpleNamespace]] | None = None,
        context: dict[str, Any] | None = None,
        cell_catalog: list[SimpleNamespace] | None = None,
    ) -> None:
        self.existing_trade_ids = list(existing_trade_ids or [])
        self.quote_ids = list(quote_ids or [])
        self.line_items_by_quote = dict(line_items_by_quote or {})
        self.context = context or {
            "context_source": "manual",
            "state": "NSW",
            "region": "metro",
            "build_type": "new_build",
            "storeys": 2,
            "spec_level": "mid",
        }
        self.cell_catalog = list(cell_catalog or [])
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.flush = AsyncMock()
        self._execute_calls = 0

    async def get(self, model: Any, ident: Any) -> Any:
        from tender.models import TenderComparison

        if model is TenderComparison:
            return SimpleNamespace(id=ident, context=self.context)
        return None

    async def execute(self, statement: Any) -> Any:
        self._execute_calls += 1
        sql = str(statement).lower()

        if "tender_project_trades" in sql:
            if sql.strip().startswith("delete") or " delete " in f" {sql} ":
                self.existing_trade_ids = []
                return _ScalarResult([])
            return _ScalarResult(self.existing_trade_ids)

        if "taxonomy_cells" in sql:
            return _ScalarResult(self.cell_catalog)

        if "tender_quotes" in sql:
            return _ScalarResult(self.quote_ids)

        if "tender_line_items" in sql:
            try:
                params = statement.compile().params
            except Exception:
                params = {}
            quote_id = None
            for value in params.values():
                if isinstance(value, uuid.UUID) and value in self.line_items_by_quote:
                    quote_id = value
                    break
            if quote_id is None and len(self.line_items_by_quote) == 1:
                quote_id = next(iter(self.line_items_by_quote))
            return _ScalarResult(self.line_items_by_quote.get(quote_id, []))

        return _ScalarResult([])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)


class _ScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = list(rows)

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


def test_generate_assigns_every_section_and_inserts_unalloc(monkeypatch) -> None:
    q1_items = [
        _item(
            figure_key="fk-1",
            description_raw="Cabinetry",
            amount_ex_gst_cents=100_00,
            counted_in_total=True,
            is_rollup=True,
        ),
        _item(
            figure_key="fk-2",
            description_raw="Roofing",
            amount_ex_gst_cents=50_00,
            counted_in_total=True,
            is_rollup=True,
        ),
    ]
    session = FakeSession(
        quote_ids=[Q1],
        line_items_by_quote={Q1: q1_items},
        cell_catalog=[
            SimpleNamespace(code="18.01", name="Cabinetry"),
            SimpleNamespace(code="12.01", name="Roofing"),
        ],
    )
    llm = FakeTaxonomyLLM(
        {
            "trades": [
                {
                    "code": "PT.01",
                    "name": "Cabinetry",
                    "description": "Cabinets and joinery",
                    "group_label": "Finishes",
                    "sort_order": 1,
                    "per_quote_sections": [{
                        "quote_id": str(Q1),
                        "figure_keys": ["fk-1"],
                    }],
                    "anchor_cell_codes": ["18.01"],
                    "confidence": 0.92,
                }
                # fk-2 deliberately omitted → auto-trade
            ]
        }
    )
    enqueue = AsyncMock()
    monkeypatch.setattr(project_taxonomy.jobs, "enqueue", enqueue)
    monkeypatch.setattr(
        project_taxonomy.settings,
        "tender_embedding_dimensions",
        8,
        raising=False,
    )

    run_async(
        project_taxonomy.generate_project_taxonomy(
            session,  # type: ignore[arg-type]
            TenderJob(
                kind="generate_project_taxonomy",
                comparison_id=COMPARISON_ID,
                payload={},
            ),
            llm_client=llm,
            embedder=FakeEmbedder(),
        )
    )

    assert llm.calls == 1
    trade_codes = {row.code for row in session.added}
    assert "PT.01" in trade_codes
    assert UNALLOCATED_TRADE_CODE in trade_codes
    auto = next(
        row
        for row in session.added
        if row.code not in {"PT.01", UNALLOCATED_TRADE_CODE}
    )
    assert auto.name == "Roofing"
    assert auto.seed_assignments == [{"quote_id": str(Q1), "figure_key": "fk-2"}]
    pt01 = next(row for row in session.added if row.code == "PT.01")
    assert pt01.seed_assignments == [{"quote_id": str(Q1), "figure_key": "fk-1"}]
    assert pt01.embedding is not None
    enqueue.assert_awaited()


def test_generate_drops_unknown_anchor_codes(monkeypatch) -> None:
    q1_items = [
        _item(
            figure_key="fk-1",
            description_raw="Cabinetry",
            amount_ex_gst_cents=100_00,
            counted_in_total=True,
            is_rollup=True,
        ),
    ]
    session = FakeSession(
        quote_ids=[Q1],
        line_items_by_quote={Q1: q1_items},
        cell_catalog=[SimpleNamespace(code="18.01", name="Cabinetry")],
    )
    llm = FakeTaxonomyLLM(
        {
            "trades": [
                {
                    "code": "PT.01",
                    "name": "Cabinetry",
                    "description": "x",
                    "group_label": "Finishes",
                    "sort_order": 1,
                    "per_quote_sections": [{
                        "quote_id": str(Q1),
                        "figure_keys": ["fk-1"],
                    }],
                    "anchor_cell_codes": ["18.01", "99.99"],
                    "confidence": 0.9,
                }
            ]
        }
    )
    monkeypatch.setattr(project_taxonomy.jobs, "enqueue", AsyncMock())
    monkeypatch.setattr(
        project_taxonomy.settings,
        "tender_embedding_dimensions",
        8,
        raising=False,
    )

    run_async(
        project_taxonomy.generate_project_taxonomy(
            session,  # type: ignore[arg-type]
            TenderJob(
                kind="generate_project_taxonomy",
                comparison_id=COMPARISON_ID,
                payload={},
            ),
            llm_client=llm,
            embedder=FakeEmbedder(),
        )
    )

    pt01 = next(row for row in session.added if row.code == "PT.01")
    assert pt01.anchor_cell_codes == ["18.01"]


def test_generate_idempotent_skips_llm_when_trades_exist(monkeypatch) -> None:
    session = FakeSession(
        existing_trade_ids=[uuid.uuid4()],
        quote_ids=[Q1, Q2],
    )
    llm = FakeTaxonomyLLM({"trades": []})
    enqueue = AsyncMock()
    monkeypatch.setattr(project_taxonomy.jobs, "enqueue", enqueue)

    run_async(
        project_taxonomy.generate_project_taxonomy(
            session,  # type: ignore[arg-type]
            TenderJob(
                kind="generate_project_taxonomy",
                comparison_id=COMPARISON_ID,
                payload={},
            ),
            llm_client=llm,
            embedder=FakeEmbedder(),
        )
    )

    assert llm.calls == 0
    assert session.added == []
    assert enqueue.await_count == 2


def test_generate_regenerate_true_reruns_llm(monkeypatch) -> None:
    q1_items = [
        _item(
            figure_key="fk-1",
            description_raw="Cabinetry",
            amount_ex_gst_cents=100_00,
            counted_in_total=True,
            is_rollup=True,
        ),
    ]
    session = FakeSession(
        existing_trade_ids=[uuid.uuid4()],
        quote_ids=[Q1],
        line_items_by_quote={Q1: q1_items},
        cell_catalog=[SimpleNamespace(code="18.01", name="Cabinetry")],
    )
    llm = FakeTaxonomyLLM(
        {
            "trades": [
                {
                    "code": "PT.01",
                    "name": "Cabinetry",
                    "description": "x",
                    "group_label": "Finishes",
                    "sort_order": 1,
                    "per_quote_sections": [{
                        "quote_id": str(Q1),
                        "figure_keys": ["fk-1"],
                    }],
                    "anchor_cell_codes": ["18.01"],
                    "confidence": 0.9,
                }
            ]
        }
    )
    monkeypatch.setattr(project_taxonomy.jobs, "enqueue", AsyncMock())
    monkeypatch.setattr(
        project_taxonomy.settings,
        "tender_embedding_dimensions",
        8,
        raising=False,
    )

    run_async(
        project_taxonomy.generate_project_taxonomy(
            session,  # type: ignore[arg-type]
            TenderJob(
                kind="generate_project_taxonomy",
                comparison_id=COMPARISON_ID,
                payload={"regenerate": True},
            ),
            llm_client=llm,
            embedder=FakeEmbedder(),
        )
    )

    assert llm.calls == 1
    assert any(row.code == "PT.01" for row in session.added)
