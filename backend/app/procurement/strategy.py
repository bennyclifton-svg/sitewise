"""Procurement Strategy domain service shared by HTTP and MCP callers."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.procurement_request import ProcurementRequest
from app.database.procurement_strategy import (
    ProcurementStrategy,
    ProcurementStrategyCandidate,
    ProcurementStrategyRow,
)
from app.sitewise.discipline_catalog import (
    RequiredProjectDiscipline,
    discipline_by_code,
    required_project_disciplines,
    resolve_discipline,
)
from app.sitewise.consultant_register import consultant_appointment_rows

STRATEGY_STATUSES = frozenset(
    {
        "not_started",
        "researching",
        "shortlisting",
        "request_drafted",
        "issued",
        "responses_received",
        "evaluating",
        "awarded",
        "cancelled",
    }
)
_STATUS_RANK = {
    "not_started": 0,
    "researching": 1,
    "shortlisting": 2,
    "request_drafted": 3,
    "issued": 4,
    "responses_received": 5,
    "evaluating": 6,
    "awarded": 7,
}


class ProcurementStrategyNotFound(LookupError):
    pass


class ProcurementStrategyConflict(RuntimeError):
    pass


class ProcurementStrategyValidationError(ValueError):
    pass


def _label_key(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _appointment_facts_by_code(project: object) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for fact in consultant_appointment_rows(project):  # type: ignore[arg-type]
        try:
            discipline = resolve_discipline(
                str(fact["discipline"]), participant_type="consultant"
            )
        except ValueError:
            continue
        current = facts.get(discipline.code)
        if current is None or _is_appointed(fact) or not _is_appointed(current):
            facts[discipline.code] = fact
    return facts


def _is_appointed(fact: dict[str, Any]) -> bool:
    return _label_key(str(fact.get("status") or "")).startswith("appointed")


def _sync_appointment_to_row(
    row: ProcurementStrategyRow,
    *,
    appointment: dict[str, Any],
    tenderer_column_count: int,
) -> bool:
    changed = False
    if _is_appointed(appointment) and row.status != "awarded":
        row.status = "awarded"
        changed = True

    firm = " ".join(str(appointment.get("firm") or "").split())
    if not firm or row.locked:
        return changed
    firm_key = _label_key(firm)
    if any(_label_key(candidate.company_name) == firm_key for candidate in row.candidates):
        return changed
    used_slots = {candidate.slot for candidate in row.candidates}
    slot = next(
        (
            candidate_slot
            for candidate_slot in range(1, tenderer_column_count + 1)
            if candidate_slot not in used_slots
        ),
        None,
    )
    if slot is None:
        return changed
    row.candidates.append(
        ProcurementStrategyCandidate(
            slot=slot,
            company_name=firm,
            source_title="Project consultant register",
        )
    )
    return True


async def _load_strategy(
    session: AsyncSession, project_id: uuid.UUID
) -> ProcurementStrategy | None:
    result = await session.execute(
        select(ProcurementStrategy)
        .where(ProcurementStrategy.project_id == project_id)
        .options(
            selectinload(ProcurementStrategy.rows).selectinload(
                ProcurementStrategyRow.candidates
            )
        )
    )
    return result.scalar_one_or_none()


async def _requirements(
    session: AsyncSession, *, project: object
) -> list[RequiredProjectDiscipline]:
    project_id = getattr(project, "id")
    requirements = list(required_project_disciplines(project))
    by_code = {row.code: row for row in requirements if row.code}
    by_label = {_label_key(row.label): row for row in requirements}
    result = await session.execute(
        select(ProcurementRequest).where(ProcurementRequest.project_id == project_id)
    )
    for request in result.scalars():
        discipline = None
        if request.discipline_code:
            try:
                discipline = discipline_by_code(request.discipline_code)
            except ValueError:
                discipline = None
        if discipline is None:
            participant = "consultant" if request.kind == "consultant_rfp" else None
            try:
                discipline = resolve_discipline(
                    request.target_name, participant_type=participant
                )
            except ValueError:
                discipline = None
        if discipline is not None:
            existing = by_code.get(discipline.code)
            sources = (
                (*existing.sources, "existing_request")
                if existing and "existing_request" not in existing.sources
                else existing.sources
                if existing
                else ("existing_request",)
            )
            row = RequiredProjectDiscipline(
                code=discipline.code,
                label=discipline.pmp_label,
                participant_type=discipline.participant_type,
                request_kind=discipline.request_kind,
                sources=sources,
            )
            if existing:
                requirements[requirements.index(existing)] = row
            else:
                requirements.append(row)
            by_code[discipline.code] = row
            continue
        key = _label_key(request.target_name)
        if key in by_label:
            continue
        participant_type = "consultant" if request.kind == "consultant_rfp" else "trade"
        row = RequiredProjectDiscipline(
            code=None,
            label=request.target_name,
            participant_type=participant_type,
            request_kind=request.kind,
            sources=("existing_request",),
        )
        requirements.append(row)
        by_label[key] = row
    return requirements


def _fingerprint(requirements: list[RequiredProjectDiscipline]) -> str:
    payload = [
        {
            "code": row.code,
            "label": row.label,
            "participant_type": row.participant_type,
            "request_kind": row.request_kind,
        }
        for row in requirements
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def _row_from_requirement(
    strategy: ProcurementStrategy,
    requirement: RequiredProjectDiscipline,
    *,
    display_order: int,
    appointment: dict[str, Any] | None = None,
) -> ProcurementStrategyRow:
    row = ProcurementStrategyRow(
        strategy_id=strategy.id,
        discipline_code=requirement.code,
        discipline_label=requirement.label,
        participant_type=requirement.participant_type,
        request_kind=requirement.request_kind,
        status="not_started",
        notes="",
        display_order=display_order,
        origin=(
            "existing_request"
            if requirement.sources == ("existing_request",)
            else "derived"
        ),
        locked=False,
    )
    if appointment is not None:
        _sync_appointment_to_row(
            row,
            appointment=appointment,
            tenderer_column_count=strategy.tenderer_column_count,
        )
    return row


async def ensure_procurement_strategy(
    session: AsyncSession, *, project: object
) -> ProcurementStrategy:
    project_id = getattr(project, "id")
    existing = await _load_strategy(session, project_id)
    if existing is not None:
        return existing
    requirements = await _requirements(session, project=project)
    appointments = _appointment_facts_by_code(project)
    strategy = ProcurementStrategy(
        id=uuid.uuid4(),
        project_id=project_id,
        revision=1,
        tenderer_column_count=3,
        source_fingerprint=_fingerprint(requirements),
    )
    strategy.rows = [
        _row_from_requirement(
            strategy,
            row,
            display_order=(index + 1) * 100,
            appointment=appointments.get(row.code or ""),
        )
        for index, row in enumerate(requirements)
    ]
    session.add(strategy)
    await session.flush()
    return await _required_strategy(session, project_id)


async def _required_strategy(
    session: AsyncSession, project_id: uuid.UUID
) -> ProcurementStrategy:
    strategy = await _load_strategy(session, project_id)
    if strategy is None:
        raise ProcurementStrategyNotFound(str(project_id))
    return strategy


async def get_procurement_strategy(
    session: AsyncSession, *, project_id: uuid.UUID
) -> ProcurementStrategy:
    return await _required_strategy(session, project_id)


async def refresh_procurement_strategy(
    session: AsyncSession, *, project: object
) -> ProcurementStrategy:
    project_id = getattr(project, "id")
    strategy = await _required_strategy(session, project_id)
    requirements = await _requirements(session, project=project)
    appointments = _appointment_facts_by_code(project)
    existing_codes = {row.discipline_code for row in strategy.rows if row.discipline_code}
    existing_labels = {_label_key(row.discipline_label) for row in strategy.rows}
    changed = False
    next_order = max((row.display_order for row in strategy.rows), default=0) + 100
    for requirement in requirements:
        if requirement.code and requirement.code in existing_codes:
            continue
        if requirement.code is None and _label_key(requirement.label) in existing_labels:
            continue
        strategy.rows.append(
            _row_from_requirement(
                strategy,
                requirement,
                display_order=next_order,
                appointment=appointments.get(requirement.code or ""),
            )
        )
        next_order += 100
        changed = True
    for row in strategy.rows:
        if row.discipline_code is None:
            continue
        appointment = appointments.get(row.discipline_code)
        if appointment is None:
            continue
        changed = (
            _sync_appointment_to_row(
                row,
                appointment=appointment,
                tenderer_column_count=strategy.tenderer_column_count,
            )
            or changed
        )
    fingerprint = _fingerprint(requirements)
    if changed or fingerprint != strategy.source_fingerprint:
        strategy.source_fingerprint = fingerprint
        strategy.revision += 1
        await session.flush()
    return await _required_strategy(session, project_id)


def _row_for(
    rows: list[ProcurementStrategyRow], row_id: uuid.UUID | None
) -> ProcurementStrategyRow:
    row = next((item for item in rows if item.id == row_id), None)
    if row is None:
        raise ProcurementStrategyValidationError("strategy row not found")
    return row


def _require_unlocked(row: ProcurementStrategyRow) -> None:
    if row.locked:
        raise ProcurementStrategyConflict(f"{row.discipline_label} is locked")


async def apply_procurement_strategy_operations(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    expected_revision: int,
    operations: list[dict[str, Any]],
) -> ProcurementStrategy:
    strategy = await _required_strategy(session, project_id)
    if expected_revision != strategy.revision:
        raise ProcurementStrategyConflict(
            f"Expected strategy revision {expected_revision}, current revision is {strategy.revision}"
        )
    if not operations or len(operations) > 50:
        raise ProcurementStrategyValidationError("operations must contain 1 to 50 items")

    rows = list(strategy.rows)
    for operation in operations:
        kind = operation.get("operation")
        if kind == "SET_TENDERER_COLUMN_COUNT":
            count = operation.get("tenderer_column_count")
            if count not in {3, 4}:
                raise ProcurementStrategyValidationError("column count must be 3 or 4")
            strategy.tenderer_column_count = count
            continue
        if kind == "ADD_ROW":
            code = operation.get("discipline_code")
            if code:
                discipline = discipline_by_code(code)
                if any(row.discipline_code == code for row in rows):
                    raise ProcurementStrategyConflict("discipline is already in the strategy")
                label = discipline.pmp_label
                participant_type = discipline.participant_type
                request_kind = discipline.request_kind
            else:
                label = " ".join(str(operation.get("discipline_label") or "").split())
                participant_type = operation.get("participant_type")
                request_kind = operation.get("request_kind")
                if not label or participant_type not in {"consultant", "trade", "supplier"}:
                    raise ProcurementStrategyValidationError(
                        "custom rows require a label and participant type"
                    )
                if request_kind not in {
                    "consultant_rfp",
                    "contractor_eoi",
                    "trade_rft",
                    "trade_rfq",
                }:
                    raise ProcurementStrategyValidationError(
                        "custom rows require a request kind"
                    )
            new_row = ProcurementStrategyRow(
                strategy_id=strategy.id,
                discipline_code=code,
                discipline_label=label,
                participant_type=participant_type,
                request_kind=request_kind,
                status=operation.get("status") or "not_started",
                notes=operation.get("notes") or "",
                display_order=0,
                origin="manual",
                locked=False,
            )
            session.add(new_row)
            before = operation.get("before_row_id")
            after = operation.get("after_row_id")
            if before:
                rows.insert(rows.index(_row_for(rows, before)), new_row)
            elif after:
                rows.insert(rows.index(_row_for(rows, after)) + 1, new_row)
            else:
                rows.append(new_row)
            continue

        row = _row_for(rows, operation.get("row_id"))
        if kind == "UNLOCK_ROW":
            row.locked = False
            continue
        if kind == "LOCK_ROW":
            row.locked = True
            continue
        _require_unlocked(row)
        if kind == "UPDATE_ROW":
            if operation.get("discipline_label") is not None:
                if row.discipline_code is not None:
                    raise ProcurementStrategyConflict(
                        "catalogue discipline labels cannot be renamed"
                    )
                label = " ".join(str(operation["discipline_label"]).split())
                if not label:
                    raise ProcurementStrategyValidationError("discipline label is required")
                row.discipline_label = label
            if operation.get("status") is not None:
                if operation["status"] not in STRATEGY_STATUSES:
                    raise ProcurementStrategyValidationError("invalid strategy status")
                row.status = operation["status"]
            if operation.get("notes") is not None:
                row.notes = str(operation["notes"])
        elif kind == "MOVE_ROW":
            rows.remove(row)
            before = operation.get("before_row_id")
            after = operation.get("after_row_id")
            if before:
                rows.insert(rows.index(_row_for(rows, before)), row)
            elif after:
                rows.insert(rows.index(_row_for(rows, after)) + 1, row)
            else:
                rows.append(row)
        elif kind == "DELETE_ROW":
            rows.remove(row)
            await session.delete(row)
        elif kind == "UPSERT_CANDIDATE":
            slot = operation.get("slot")
            company = " ".join(str(operation.get("company_name") or "").split())
            if not isinstance(slot, int) or slot < 1 or slot > strategy.tenderer_column_count:
                raise ProcurementStrategyValidationError("candidate slot is not visible")
            if not company:
                raise ProcurementStrategyValidationError("company name is required")
            candidate = next((item for item in row.candidates if item.slot == slot), None)
            if candidate is None:
                candidate = ProcurementStrategyCandidate(
                    slot=slot, company_name=company
                )
                row.candidates.append(candidate)
            candidate.company_name = company
            candidate.website_url = operation.get("website_url")
            candidate.location_text = operation.get("location_text")
            candidate.source_url = operation.get("source_url")
            candidate.source_title = operation.get("source_title")
            if candidate.source_url:
                candidate.researched_at = datetime.now(UTC)
        elif kind == "CLEAR_CANDIDATE":
            slot = operation.get("slot")
            candidate = next((item for item in row.candidates if item.slot == slot), None)
            if candidate is not None:
                row.candidates.remove(candidate)
                await session.delete(candidate)
        else:
            raise ProcurementStrategyValidationError(f"unsupported operation: {kind}")

    for index, row in enumerate(rows):
        row.display_order = (index + 1) * 100
    strategy.revision += 1
    await session.flush()
    return await _required_strategy(session, project_id)


async def strategy_snapshot(
    session: AsyncSession,
    *,
    strategy: ProcurementStrategy,
    project: object | None = None,
) -> dict[str, Any]:
    linked_result = await session.execute(
        select(ProcurementRequest).where(
            ProcurementRequest.project_id == strategy.project_id,
            ProcurementRequest.strategy_row_id.is_not(None),
        )
    )
    linked: dict[uuid.UUID, list[uuid.UUID]] = {}
    for request in linked_result.scalars():
        linked.setdefault(request.strategy_row_id, []).append(request.id)

    live_codes: set[str] = set()
    live_labels: set[str] = set()
    if project is not None:
        for requirement in await _requirements(session, project=project):
            if requirement.code:
                live_codes.add(requirement.code)
            else:
                live_labels.add(_label_key(requirement.label))
    rows = []
    for row in sorted(strategy.rows, key=lambda item: item.display_order):
        no_longer_required = False
        if project is not None and row.origin == "derived" and not row.locked:
            no_longer_required = (
                row.discipline_code not in live_codes
                if row.discipline_code
                else _label_key(row.discipline_label) not in live_labels
            )
        rows.append(
            {
                "id": row.id,
                "discipline_code": row.discipline_code,
                "discipline_label": row.discipline_label,
                "participant_type": row.participant_type,
                "request_kind": row.request_kind,
                "status": row.status,
                "notes": row.notes,
                "display_order": row.display_order,
                "origin": row.origin,
                "locked": row.locked,
                "linked_request_ids": linked.get(row.id, []),
                "no_longer_required": no_longer_required,
                "candidates": [
                    {
                        "id": candidate.id,
                        "slot": candidate.slot,
                        "company_name": candidate.company_name,
                        "website_url": candidate.website_url,
                        "location_text": candidate.location_text,
                        "source_url": candidate.source_url,
                        "source_title": candidate.source_title,
                        "researched_at": candidate.researched_at,
                    }
                    for candidate in sorted(row.candidates, key=lambda item: item.slot)
                ],
            }
        )
    return {
        "id": strategy.id,
        "project_id": strategy.project_id,
        "revision": strategy.revision,
        "tenderer_column_count": strategy.tenderer_column_count,
        "source_fingerprint": strategy.source_fingerprint,
        "rows": rows,
        "created_at": strategy.created_at,
        "updated_at": strategy.updated_at,
    }


async def link_request_to_strategy_row(
    session: AsyncSession,
    *,
    request: ProcurementRequest,
    discipline_code: str | None = None,
    strategy_row_id: uuid.UUID | None = None,
) -> ProcurementStrategyRow | None:
    """Attach a request to its canonical row, validating project and request kind."""
    explicit_row = strategy_row_id is not None
    if discipline_code is not None:
        discipline = discipline_by_code(discipline_code)
        if discipline.request_kind != request.kind:
            raise ProcurementStrategyValidationError(
                "discipline request kind does not match the procurement request"
            )
        request.discipline_code = discipline.code
    if discipline_code is None and strategy_row_id is None:
        participant_type = "consultant" if request.kind == "consultant_rfp" else None
        try:
            discipline_code = resolve_discipline(
                request.target_name, participant_type=participant_type
            ).code
        except ValueError:
            return None
    statement = (
        select(ProcurementStrategyRow)
        .join(ProcurementStrategy)
        .where(ProcurementStrategy.project_id == request.project_id)
    )
    if strategy_row_id is not None:
        statement = statement.where(ProcurementStrategyRow.id == strategy_row_id)
    if discipline_code is not None:
        statement = statement.where(
            ProcurementStrategyRow.discipline_code == discipline_code
        )
    row = (await session.execute(statement)).scalar_one_or_none()
    if row is None:
        if explicit_row:
            raise ProcurementStrategyValidationError(
                "strategy row does not belong to this project"
            )
        return None
    if row.request_kind != request.kind:
        raise ProcurementStrategyValidationError(
            "strategy row request kind does not match the procurement request"
        )
    request.strategy_row_id = row.id
    request.discipline_code = row.discipline_code
    return row


async def advance_strategy_status(
    session: AsyncSession,
    *,
    request: ProcurementRequest,
    status: str,
) -> None:
    """Reflect authoritative request lifecycle events without overriding later states."""
    if request.strategy_row_id is None or status not in STRATEGY_STATUSES:
        return
    row = await session.get(ProcurementStrategyRow, request.strategy_row_id)
    if row is None:
        return
    should_update = status in {"cancelled", "awarded"} or (
        row.status not in {"cancelled", "awarded"}
        and _STATUS_RANK.get(status, -1) > _STATUS_RANK.get(row.status, -1)
    )
    if not should_update:
        return
    row.status = status
    strategy = await session.get(ProcurementStrategy, row.strategy_id)
    if strategy is not None:
        strategy.revision += 1
    await session.flush()


async def record_consultant_appointment(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    discipline: str,
    firm: str,
) -> bool:
    """Mark an appointed consultant and retain the selected firm in its row."""
    try:
        canonical = resolve_discipline(discipline, participant_type="consultant")
    except ValueError:
        return False
    result = await session.execute(
        select(ProcurementStrategyRow)
        .join(ProcurementStrategy)
        .where(
            ProcurementStrategy.project_id == project_id,
            ProcurementStrategyRow.discipline_code == canonical.code,
        )
        .options(selectinload(ProcurementStrategyRow.candidates))
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    strategy = await session.get(ProcurementStrategy, row.strategy_id)
    if strategy is None:
        return False
    changed = _sync_appointment_to_row(
        row,
        appointment={"firm": firm, "status": "Appointed"},
        tenderer_column_count=strategy.tenderer_column_count,
    )
    if changed:
        strategy.revision += 1
        await session.flush()
    return True
