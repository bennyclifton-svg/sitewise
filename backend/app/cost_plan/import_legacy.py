from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.calculations import calculate_totals, resolved_budget
from app.cost_plan.models import CostPlanItem, CostPlanVersion
from app.cost_plan.schemas import CostItemInput, DependencySnapshot
from app.database.draft_artifact import DraftArtifact


@dataclass(frozen=True, slots=True)
class LegacyImportResult:
    source_draft_id: uuid.UUID
    source_version: int
    items: tuple[CostItemInput, ...]
    warnings: tuple[str, ...]
    source_budget_total: Decimal | None
    parsed_budget_total: Decimal
    applied: bool = False
    typed_version_id: uuid.UUID | None = None


def _cells(line: str) -> list[str]:
    return [
        re.sub(r"(\*\*|__|`)", "", cell).strip()
        for cell in line.strip().strip("|").split("|")
    ]


def _header(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return {"cost item": "item", "cost items": "item", "amount": "budget"}.get(
        value, value
    )


def _money(value: str) -> Decimal | None:
    cleaned = value.strip().lower().replace("$", "").replace(",", "")
    if not cleaned or cleaned in {"-", "--", "n/a", "na", "tbc"}:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("() ")
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([mk])?", cleaned)
    if match is None:
        return None
    try:
        amount = Decimal(match.group(1))
    except InvalidOperation:
        return None
    if match.group(2) == "m":
        amount *= Decimal("1000000")
    elif match.group(2) == "k":
        amount *= Decimal("1000")
    return -amount if negative else amount


def parse_legacy_draft(draft: DraftArtifact) -> LegacyImportResult:
    lines = draft.content_markdown.splitlines()
    tables: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip().startswith("|") and line.strip().endswith("|"):
            current.append(line)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)

    table: list[str] | None = None
    headers: list[str] = []
    for candidate in tables:
        candidate_headers = [_header(value) for value in _cells(candidate[0])]
        if {"cost code", "category", "item", "budget"}.issubset(candidate_headers):
            table = candidate
            headers = candidate_headers
            break

    warnings: list[str] = []
    items: list[CostItemInput] = []
    if table is None:
        warnings.append(
            "Cost breakdown table with typed identity columns was not found."
        )
    else:
        index = {name: position for position, name in enumerate(headers)}
        for row_number, line in enumerate(table[1:], start=2):
            values = _cells(line)
            if all(
                not value.replace("-", "").replace(":", "").strip() for value in values
            ):
                continue

            def value(name: str) -> str:
                position = index.get(name)
                return (
                    values[position].strip()
                    if position is not None and position < len(values)
                    else ""
                )

            cost_code = value("cost code")
            category = value("category")
            item_name = value("item")
            if "total" in f"{cost_code} {category} {item_name}".lower():
                continue
            budget = _money(value("budget"))
            if not cost_code or not category or not item_name or budget is None:
                warnings.append(
                    f"Row {row_number} was not imported because required typed values were missing or invalid."
                )
                continue
            try:
                items.append(
                    CostItemInput(
                        item_key=cost_code.lower().replace(" ", "-"),
                        cost_code=cost_code,
                        category=category,
                        item=item_name,
                        budget=budget,
                        committed=_money(value("approved contract")) or Decimal("0"),
                        forecast=_money(value("forecast")) or Decimal("0"),
                        paid=_money(value("paid")) or Decimal("0"),
                        basis=value("basis") or "Legacy accepted Cost Plan draft",
                        status="confirmed",
                        source_refs=[
                            {"draft_id": str(draft.id), "version": draft.version}
                        ],
                    )
                )
            except ValidationError as exc:
                warnings.append(
                    f"Row {row_number} was not imported: {exc.errors()[0]['msg']}."
                )

    parsed_total = sum((resolved_budget(item) for item in items), Decimal("0"))
    source_total = None
    for line in lines:
        if "total ex gst" in line.lower() or "grand total" in line.lower():
            candidates = [_money(cell) for cell in _cells(line)]
            source_total = next(
                (amount for amount in reversed(candidates) if amount is not None), None
            )
            if source_total is not None:
                break
    if source_total is not None and source_total != parsed_total:
        warnings.append(
            f"Parsed budget total {parsed_total:.2f} does not reconcile with source total {source_total:.2f}."
        )
    return LegacyImportResult(
        source_draft_id=draft.id,
        source_version=draft.version,
        items=tuple(items),
        warnings=tuple(warnings),
        source_budget_total=source_total,
        parsed_budget_total=parsed_total,
    )


async def import_legacy_draft(
    session: AsyncSession,
    *,
    draft: DraftArtifact,
    apply: bool = False,
    require_accepted: bool = True,
) -> LegacyImportResult:
    if draft.workflow_type != "create_cost_plan" or (
        require_accepted and draft.status != "accepted"
    ):
        raise ValueError("only accepted Cost Plan drafts can be imported")
    parsed = parse_legacy_draft(draft)
    if not apply:
        return parsed
    if (
        require_accepted
        and parsed.source_budget_total is not None
        and parsed.source_budget_total != parsed.parsed_budget_total
    ):
        raise ValueError("legacy Cost Plan totals do not reconcile")
    existing = (
        await session.execute(
            select(CostPlanVersion)
            .where(
                CostPlanVersion.project_id == draft.project_id,
                CostPlanVersion.source_draft_id == draft.id,
            )
            .options(selectinload(CostPlanVersion.items))
        )
    ).scalar_one_or_none()
    if existing is not None:
        return replace(parsed, applied=False, typed_version_id=existing.id)

    provenance = (
        draft.provenance_metadata if isinstance(draft.provenance_metadata, dict) else {}
    )
    dependency_data = provenance.get("dependency_snapshot")
    if isinstance(dependency_data, dict):
        dependencies = DependencySnapshot.model_validate(dependency_data)
    else:
        dependencies = DependencySnapshot(
            profile_revision=max(int(provenance.get("profile_revision", 1)), 1),
            evidence_fingerprint=str(
                provenance.get("evidence_fingerprint") or "legacy-unknown"
            ),
            decision_set_revision=max(
                int(provenance.get("decision_set_revision", 1)), 1
            ),
            runtime_version=draft.runtime,
            model_version=draft.model,
        )
    totals = calculate_totals(
        list(parsed.items),
        contingency_percent=Decimal("0"),
        escalation_percent=Decimal("0"),
        gst_treatment="exclusive",
    )
    row = CostPlanVersion(
        project_id=draft.project_id,
        artefact_revision_id=draft.id,
        version=draft.version,
        created_by_user_id=draft.author_user_id,
        status="accepted" if draft.status == "accepted" else "proposed",
        contingency_percent=Decimal("0"),
        escalation_percent=Decimal("0"),
        gst_treatment="exclusive",
        assumptions={
            "legacy_import": "Imported from accepted Markdown; GST assumed exclusive."
        },
        narrative={},
        dependency_snapshot=dependencies.model_dump(mode="json"),
        deterministic_totals=totals.model_dump(mode="json"),
        source_draft_id=draft.id,
    )
    row.items = [
        CostPlanItem(
            **item.model_dump(exclude={"budget"}),
            budget=resolved_budget(item),
        )
        for item in parsed.items
    ]
    session.add(row)
    await session.flush()
    return LegacyImportResult(
        source_draft_id=parsed.source_draft_id,
        source_version=parsed.source_version,
        items=parsed.items,
        warnings=parsed.warnings,
        source_budget_total=parsed.source_budget_total,
        parsed_budget_total=parsed.parsed_budget_total,
        applied=True,
        typed_version_id=row.id,
    )
