from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from tender.models import (
    TaxonomySynonym,
    TenderCorrection,
    TenderLineItem,
    TenderMapping,
    TenderProjectTrade,
)
from tender.services.corrections import record_mapping_correction
from tender.services.mapping import t0_match
from tests.conftest import run_async


def test_record_mapping_correction_updates_mapping_and_writes_correction() -> None:
    reviewer_id = uuid.uuid4()
    session = FakeCorrectionSession()

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_cell_code="03.05",
            reviewer_id=reviewer_id,
            reason="Wrong site-cost bucket",
        )
    )

    correction = _only_added(session, TenderCorrection)
    assert correction.entity_type == "tender_mapping"
    assert correction.entity_id == session.mapping.id
    assert correction.field == "cell_code"
    assert correction.before == {
        "cell_code": "03.01",
        "project_trade_id": None,
        "tier": "t1_embedding",
        "qa_state": "needs_review",
    }
    assert correction.after == {
        "cell_code": "03.05",
        "project_trade_id": None,
        "tier": "human",
        "qa_state": "corrected",
    }
    assert correction.reviewer == reviewer_id
    assert session.mapping.cell_code == "03.05"
    assert session.mapping.project_trade_id is None
    assert session.mapping.tier == "human"
    assert session.mapping.qa_state == "corrected"
    assert session.mapping.reviewed_by == reviewer_id
    assert session.mapping.reviewed_at is not None


def test_record_mapping_correction_inserts_normalized_synonym() -> None:
    session = FakeCorrectionSession()

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_cell_code="03.05",
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )

    synonym = _only_added(session, TaxonomySynonym)
    assert synonym.cell_code == "03.05"
    assert synonym.phrase == " Retaining   WALL allowance "
    assert synonym.phrase_norm == "retaining wall allowance"
    assert synonym.source == "correction"
    assert float(synonym.confidence) == 1.0
    assert synonym.correction_id is not None


def test_record_mapping_correction_duplicate_synonym_is_noop() -> None:
    session = FakeCorrectionSession(
        existing_synonym=TaxonomySynonym(
            cell_code="03.05",
            phrase="Retaining wall allowance",
            phrase_norm="retaining wall allowance",
            source="correction",
        )
    )

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_cell_code="03.05",
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )

    assert not [obj for obj in session.added if isinstance(obj, TaxonomySynonym)]


def test_correction_synonym_can_be_picked_up_by_t0_next_run() -> None:
    session = FakeCorrectionSession()
    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_cell_code="03.05",
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )
    synonym = _only_added(session, TaxonomySynonym)
    t0_session = FakeT0Session(
        [SimpleNamespace(cell_code=synonym.cell_code, phrase=synonym.phrase)]
    )

    result = run_async(t0_match(t0_session, synonym.phrase_norm))

    assert result[0].cell_code == "03.05"
    assert result[0].via == "exact"


def test_record_mapping_correction_trade_path_sets_trade_and_clears_cell() -> None:
    reviewer_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    session = FakeCorrectionSession(
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=uuid.uuid4(),
            code="PT.JOINERY",
            name="Joinery / cabinetry",
            sort_order=1,
            source="generated",
            anchor_cell_codes=["08.01"],
            seed_assignments=[],
        )
    )

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_project_trade_id=trade_id,
            reviewer_id=reviewer_id,
            reason="Reassign to joinery trade",
        )
    )

    correction = _only_added(session, TenderCorrection)
    assert correction.field == "project_trade_id"
    assert correction.after == {
        "cell_code": None,
        "project_trade_id": str(trade_id),
        "tier": "human",
        "qa_state": "corrected",
    }
    assert session.mapping.project_trade_id == trade_id
    assert session.mapping.cell_code is None
    assert session.mapping.tier == "human"
    assert session.mapping.qa_state == "corrected"


def test_record_mapping_correction_trade_single_anchor_upserts_synonym() -> None:
    trade_id = uuid.uuid4()
    session = FakeCorrectionSession(
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=uuid.uuid4(),
            code="PT.JOINERY",
            name="Joinery / cabinetry",
            sort_order=1,
            source="generated",
            anchor_cell_codes=["08.01"],
            seed_assignments=[],
        )
    )

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_project_trade_id=trade_id,
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )

    synonym = _only_added(session, TaxonomySynonym)
    assert synonym.cell_code == "08.01"
    assert synonym.phrase_norm == "retaining wall allowance"
    assert synonym.source == "correction"


def test_record_mapping_correction_trade_skips_synonym_when_zero_anchors() -> None:
    trade_id = uuid.uuid4()
    session = FakeCorrectionSession(
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=uuid.uuid4(),
            code="PT.UNALLOC",
            name="Unallocated",
            sort_order=10_000,
            source="reserved",
            anchor_cell_codes=[],
            seed_assignments=[],
        )
    )

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_project_trade_id=trade_id,
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )

    assert session.mapping.project_trade_id == trade_id
    assert not [obj for obj in session.added if isinstance(obj, TaxonomySynonym)]


def test_record_mapping_correction_trade_skips_synonym_when_multi_anchor() -> None:
    trade_id = uuid.uuid4()
    session = FakeCorrectionSession(
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=uuid.uuid4(),
            code="PT.STRUCT",
            name="Structure",
            sort_order=2,
            source="generated",
            anchor_cell_codes=["03.01", "03.05"],
            seed_assignments=[],
        )
    )

    run_async(
        record_mapping_correction(
            session,
            mapping_id=session.mapping.id,
            corrected_project_trade_id=trade_id,
            reviewer_id=uuid.uuid4(),
            reason=None,
        )
    )

    assert session.mapping.project_trade_id == trade_id
    assert not [obj for obj in session.added if isinstance(obj, TaxonomySynonym)]


class FakeCorrectionSession:
    def __init__(
        self,
        existing_synonym: TaxonomySynonym | None = None,
        trade: TenderProjectTrade | None = None,
    ) -> None:
        self.mapping = TenderMapping(
            id=uuid.uuid4(),
            line_item_id=uuid.uuid4(),
            cell_code="03.01",
            project_trade_id=None,
            tier="t1_embedding",
            qa_state="needs_review",
            confidence=0.82,
        )
        self.line_item = TenderLineItem(
            id=self.mapping.line_item_id,
            quote_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            page_no=1,
            description_raw=" Retaining   WALL allowance ",
            item_status="included",
        )
        self.existing_synonym = existing_synonym
        self.trade = trade
        self.added: list[Any] = []

    async def get(self, model: type, ident: uuid.UUID) -> object | None:
        if model is TenderMapping and ident == self.mapping.id:
            return self.mapping
        if model is TenderLineItem and ident == self.line_item.id:
            return self.line_item
        if (
            model is TenderProjectTrade
            and self.trade is not None
            and ident == self.trade.id
        ):
            return self.trade
        return None

    async def execute(self, statement: Any) -> "FakeResult":
        return FakeResult(self.existing_synonym)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


class FakeResult:
    def __init__(self, item: object | None) -> None:
        self.item = item

    def scalars(self) -> "FakeResult":
        return self

    def first(self) -> object | None:
        return self.item


class FakeT0Session:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows

    async def execute(self, statement: Any) -> "FakeT0Result":
        return FakeT0Result(self.rows)


class FakeT0Result:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self.rows


def _only_added(session: FakeCorrectionSession, model: type) -> Any:
    matches = [obj for obj in session.added if isinstance(obj, model)]
    assert len(matches) == 1
    return matches[0]
