from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, Float, Integer, String, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    TenderCellStatus,
    TenderCorrection,
    TenderDocument,
    TenderFlag,
    TenderLineItem,
    TenderMapping,
    TenderQuote,
)
from tender.schemas import QAResolveRequest, QAReviewItem
from tender.services.corrections import record_mapping_correction


class QAItemNotFoundError(ValueError):
    pass


class InvalidQAResolutionError(ValueError):
    pass


class PendingReviewError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QAResolveResult:
    id: uuid.UUID
    entity_type: str
    action: str
    qa_state: str | None


def review_queue_statement(comparison_id: uuid.UUID):
    cell_statuses = select(
        TenderCellStatus.id.label("item_id"),
        literal("cell_status", type_=String()).label("entity_type"),
        literal(0, type_=Integer()).label("entity_priority"),
        func.coalesce(TenderCellStatus.amount_cents, 0)
        .cast(BigInteger)
        .label("report_impact_cents"),
        TenderCellStatus.confidence.cast(Float).label("confidence"),
    ).where(
        TenderCellStatus.comparison_id == comparison_id,
        TenderCellStatus.qa_state == "needs_review",
    )
    mappings = (
        select(
            TenderMapping.id.label("item_id"),
            literal("mapping", type_=String()).label("entity_type"),
            literal(1, type_=Integer()).label("entity_priority"),
            func.coalesce(
                TenderLineItem.amount_cents,
                TenderLineItem.allowance_cents,
                0,
            )
            .cast(BigInteger)
            .label("report_impact_cents"),
            TenderMapping.confidence.cast(Float).label("confidence"),
        )
        .join(TenderLineItem, TenderLineItem.id == TenderMapping.line_item_id)
        .join(TenderQuote, TenderQuote.id == TenderLineItem.quote_id)
        .where(
            TenderQuote.comparison_id == comparison_id,
            TenderMapping.qa_state == "needs_review",
        )
    )
    flags = select(
        TenderFlag.id.label("item_id"),
        literal("flag", type_=String()).label("entity_type"),
        literal(2, type_=Integer()).label("entity_priority"),
        literal(0, type_=BigInteger()).label("report_impact_cents"),
        literal(None, type_=Float()).label("confidence"),
    ).where(
        TenderFlag.comparison_id == comparison_id,
        TenderFlag.qa_state == "needs_review",
    )
    documents = (
        select(
            TenderDocument.id.label("item_id"),
            literal("document_classification", type_=String()).label("entity_type"),
            literal(3, type_=Integer()).label("entity_priority"),
            literal(0, type_=BigInteger()).label("report_impact_cents"),
            TenderDocument.classification_confidence.cast(Float).label("confidence"),
        )
        .join(TenderQuote, TenderQuote.id == TenderDocument.quote_id)
        .where(
            TenderQuote.comparison_id == comparison_id,
            TenderDocument.doc_type.is_(None),
        )
    )

    review_items = union_all(cell_statuses, mappings, flags, documents).subquery(
        "review_items"
    )
    return (
        select(
            review_items.c.item_id,
            review_items.c.entity_type,
            review_items.c.report_impact_cents,
            review_items.c.confidence,
        )
        .order_by(
            review_items.c.entity_priority.asc(),
            review_items.c.report_impact_cents.desc(),
            review_items.c.confidence.asc().nulls_last(),
        )
    )


async def list_review_items(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> list[QAReviewItem]:
    result = await session.execute(review_queue_statement(comparison_id))
    rows = result.mappings().all()
    return [await _review_item_from_row(session, row) for row in rows]


async def get_item_comparison_id(
    session: AsyncSession,
    *,
    item_id: uuid.UUID,
) -> uuid.UUID:
    cell_status = await session.get(TenderCellStatus, item_id)
    if cell_status is not None:
        return cell_status.comparison_id

    mapping = await session.get(TenderMapping, item_id)
    if mapping is not None:
        line_item = await session.get(TenderLineItem, mapping.line_item_id)
        quote = await session.get(TenderQuote, line_item.quote_id)
        return quote.comparison_id

    flag = await session.get(TenderFlag, item_id)
    if flag is not None:
        return flag.comparison_id

    document = await session.get(TenderDocument, item_id)
    if document is not None:
        quote = await session.get(TenderQuote, document.quote_id)
        return quote.comparison_id

    raise QAItemNotFoundError(f"unknown QA item: {item_id}")


async def resolve_qa_item(
    session: AsyncSession,
    *,
    item_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    request: QAResolveRequest,
) -> QAResolveResult:
    cell_status = await session.get(TenderCellStatus, item_id)
    if cell_status is not None:
        return await _resolve_cell_status(
            session,
            cell_status,
            reviewer_id=reviewer_id,
            request=request,
        )

    mapping = await session.get(TenderMapping, item_id)
    if mapping is not None:
        return await _resolve_mapping(
            session,
            mapping,
            reviewer_id=reviewer_id,
            request=request,
        )

    flag = await session.get(TenderFlag, item_id)
    if flag is not None:
        return await _resolve_flag(
            session,
            flag,
            reviewer_id=reviewer_id,
            request=request,
        )

    document = await session.get(TenderDocument, item_id)
    if document is not None:
        return await _resolve_document(
            session,
            document,
            reviewer_id=reviewer_id,
            request=request,
        )

    raise QAItemNotFoundError(f"unknown QA item: {item_id}")


async def assert_no_pending_review(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> None:
    pending = review_queue_statement(comparison_id).subquery("pending_review")
    result = await session.execute(select(func.count()).select_from(pending))
    if result.scalar():
        raise PendingReviewError("Comparison has QA items still needing review")


async def _review_item_from_row(session: AsyncSession, row: Any) -> QAReviewItem:
    item_id = row["item_id"]
    entity_type = row["entity_type"]
    payload: dict[str, Any] = {}
    if entity_type == "cell_status":
        entity = await session.get(TenderCellStatus, item_id)
        payload = {
            "quote_id": str(entity.quote_id),
            "cell_code": entity.cell_code,
            "status": entity.status,
            "amount_cents": entity.amount_cents,
            "evidence": entity.evidence or {},
        }
    elif entity_type == "mapping":
        entity = await session.get(TenderMapping, item_id)
        line_item = await session.get(TenderLineItem, entity.line_item_id)
        payload = {
            "line_item_id": str(entity.line_item_id),
            "cell_code": entity.cell_code,
            "tier": entity.tier,
            "description_raw": line_item.description_raw,
        }
    elif entity_type == "flag":
        entity = await session.get(TenderFlag, item_id)
        payload = {
            "quote_id": str(entity.quote_id) if entity.quote_id else None,
            "cell_code": entity.cell_code,
            "flag_type": entity.flag_type,
            "severity": entity.severity,
            "headline": entity.headline,
            "detail": entity.detail,
        }
    else:
        entity = await session.get(TenderDocument, item_id)
        payload = {
            "quote_id": str(entity.quote_id),
            "filename": entity.original_filename,
            "doc_type": entity.doc_type,
        }
    return QAReviewItem(
        id=item_id,
        entity_type=entity_type,
        report_impact_cents=row["report_impact_cents"] or 0,
        confidence=row["confidence"],
        payload=payload,
    )


async def _resolve_cell_status(
    session: AsyncSession,
    cell_status: TenderCellStatus,
    *,
    reviewer_id: uuid.UUID,
    request: QAResolveRequest,
) -> QAResolveResult:
    if request.action == "suppress":
        raise InvalidQAResolutionError("cell statuses cannot be suppressed")

    before = _cell_status_snapshot(cell_status)
    if request.action == "accept":
        cell_status.qa_state = "confirmed"
    else:
        values = request.corrected_value or {}
        for field in ("status", "amount_cents", "bundled_into_cell", "evidence", "confidence"):
            if field in values:
                setattr(cell_status, field, values[field])
        cell_status.qa_state = "corrected"
    cell_status.reviewed_by = reviewer_id
    cell_status.reviewed_at = datetime.now(timezone.utc)
    _add_correction(
        session,
        entity_type="tender_cell_status",
        entity_id=cell_status.id,
        field="cell_status",
        before=before,
        after=_cell_status_snapshot(cell_status),
        reviewer_id=reviewer_id,
        reason=request.reason,
    )
    await session.flush()
    return QAResolveResult(
        id=cell_status.id,
        entity_type="cell_status",
        action=request.action,
        qa_state=cell_status.qa_state,
    )


async def _resolve_mapping(
    session: AsyncSession,
    mapping: TenderMapping,
    *,
    reviewer_id: uuid.UUID,
    request: QAResolveRequest,
) -> QAResolveResult:
    if request.action == "suppress":
        raise InvalidQAResolutionError("mappings cannot be suppressed")
    if request.action == "correct":
        corrected_value = request.corrected_value or {}
        cell_code = corrected_value.get("cell_code")
        if not isinstance(cell_code, str) or not cell_code:
            raise InvalidQAResolutionError("mapping correction requires cell_code")
        await record_mapping_correction(
            session,
            mapping_id=mapping.id,
            corrected_cell_code=cell_code,
            reviewer_id=reviewer_id,
            reason=request.reason,
        )
        return QAResolveResult(
            id=mapping.id,
            entity_type="mapping",
            action=request.action,
            qa_state="corrected",
        )

    before = _mapping_snapshot(mapping)
    mapping.qa_state = "confirmed"
    mapping.reviewed_by = reviewer_id
    mapping.reviewed_at = datetime.now(timezone.utc)
    _add_correction(
        session,
        entity_type="tender_mapping",
        entity_id=mapping.id,
        field="qa_state",
        before=before,
        after=_mapping_snapshot(mapping),
        reviewer_id=reviewer_id,
        reason=request.reason,
    )
    await session.flush()
    return QAResolveResult(
        id=mapping.id,
        entity_type="mapping",
        action=request.action,
        qa_state=mapping.qa_state,
    )


async def _resolve_flag(
    session: AsyncSession,
    flag: TenderFlag,
    *,
    reviewer_id: uuid.UUID,
    request: QAResolveRequest,
) -> QAResolveResult:
    before = _flag_snapshot(flag)
    if request.action == "suppress":
        flag.qa_state = "suppressed"
        flag.include_in_report = False
    else:
        values = request.corrected_value or {}
        for field in ("severity", "headline", "detail", "include_in_report"):
            if field in values:
                setattr(flag, field, values[field])
        flag.qa_state = "confirmed"
    _add_correction(
        session,
        entity_type="tender_flag",
        entity_id=flag.id,
        field="flag",
        before=before,
        after=_flag_snapshot(flag),
        reviewer_id=reviewer_id,
        reason=request.reason,
    )
    await session.flush()
    return QAResolveResult(
        id=flag.id,
        entity_type="flag",
        action=request.action,
        qa_state=flag.qa_state,
    )


async def _resolve_document(
    session: AsyncSession,
    document: TenderDocument,
    *,
    reviewer_id: uuid.UUID,
    request: QAResolveRequest,
) -> QAResolveResult:
    if request.action == "suppress":
        raise InvalidQAResolutionError("document classifications cannot be suppressed")
    before = _document_snapshot(document)
    if request.action == "correct":
        corrected_value = request.corrected_value or {}
        doc_type = corrected_value.get("doc_type")
        if not isinstance(doc_type, str) or not doc_type:
            raise InvalidQAResolutionError("document correction requires doc_type")
        document.doc_type = doc_type
        document.classification_confidence = 1.0
    _add_correction(
        session,
        entity_type="tender_document",
        entity_id=document.id,
        field="doc_type",
        before=before,
        after=_document_snapshot(document),
        reviewer_id=reviewer_id,
        reason=request.reason,
    )
    await session.flush()
    return QAResolveResult(
        id=document.id,
        entity_type="document_classification",
        action=request.action,
        qa_state=None,
    )


def _add_correction(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    field: str,
    before: dict,
    after: dict,
    reviewer_id: uuid.UUID,
    reason: str | None,
) -> None:
    session.add(
        TenderCorrection(
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            before=before,
            after=after,
            reviewer=reviewer_id,
            reason=reason,
        )
    )


def _cell_status_snapshot(cell_status: TenderCellStatus) -> dict:
    return {
        "status": cell_status.status,
        "amount_cents": cell_status.amount_cents,
        "bundled_into_cell": cell_status.bundled_into_cell,
        "evidence": cell_status.evidence or {},
        "confidence": float(cell_status.confidence) if cell_status.confidence is not None else None,
        "qa_state": cell_status.qa_state,
    }


def _mapping_snapshot(mapping: TenderMapping) -> dict:
    return {
        "cell_code": mapping.cell_code,
        "tier": mapping.tier,
        "confidence": float(mapping.confidence) if mapping.confidence is not None else None,
        "qa_state": mapping.qa_state,
    }


def _flag_snapshot(flag: TenderFlag) -> dict:
    return {
        "severity": flag.severity,
        "headline": flag.headline,
        "detail": flag.detail,
        "include_in_report": flag.include_in_report,
        "qa_state": flag.qa_state,
    }


def _document_snapshot(document: TenderDocument) -> dict:
    return {
        "doc_type": document.doc_type,
        "classification_confidence": (
            float(document.classification_confidence)
            if document.classification_confidence is not None
            else None
        ),
    }
