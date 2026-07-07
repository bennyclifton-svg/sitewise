"""Bounded LLM narrative slice for hybrid Create Cost Plan."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from app.assistant.chat_models import resolve_chat_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.project import Project
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack
from app.sitewise.mobilisation_evidence import (
    GAP_CERTIFIER,
    GAP_GEOTECHNICAL,
    GAP_MASTER_PROGRAMME,
    pack_has_gap,
)
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.pmp_narrative import RiskRow, format_risk_rows_table

_INSTRUCTIONS_PATH = Path(__file__).with_name("cost_plan_narrative_instructions.md")
_ISO_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

_FEE_CEILING_MISREAD_PATTERNS: tuple[str, ...] = (
    r"architect fees?.*exceed",
    r"fee[s]?\s+(?:outlined\s+at\s+)?\$?[\d,]+\s+exceed",
    r"exceed(?:ing|s)?\s+(?:the\s+)?(?:allocated\s+)?(?:construction\s+)?ceiling",
)

_FORBIDDEN_BUDGET_PHRASES: tuple[str, ...] = (
    "feasibility study",
    "$1,500,000",
    "1,500,000",
)

_GEOTECH_COMMISSION_PHRASES: tuple[str, ...] = (
    "commission geotechnical",
    "engage a geotechnical consultant",
    "engage a qualified geotechnical consultant",
    "lack of a geotechnical report",
    "ensure geotechnical report is commissioned",
)

_MASTER_PROGRAMME_MISSING_PHRASES: tuple[str, ...] = (
    "draft a master programme",
    "develop and formalise a comprehensive master programme",
    "inadequate programme management",
)

_GENERIC_RISK_OWNERS: frozenset[str] = frozenset(
    {"project team", "team", "project", "tbc", "n/a", "various", "all"}
)


def _money_variants(value: str | None) -> set[str]:
    if not value:
        return set()
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned.isdigit():
        return {value.strip()}
    amount = int(cleaned)
    return {str(amount), f"{amount:,}", f"${amount:,}"}


class CostPlanNarrativeOutput(BaseModel):
    judgements: list[str] = Field(min_length=2)
    recommendations: list[str] = Field(min_length=3)
    risk_rows: list[RiskRow] = Field(min_length=5)
    next_steps: list[str] = Field(min_length=3)

    @field_validator("next_steps")
    @classmethod
    def validate_next_steps(cls, values: list[str]) -> list[str]:
        if len(values) < 3:
            msg = "next_steps must include at least 3 items"
            raise ValueError(msg)
        return values


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


cost_plan_narrative_agent = Agent(
    f"openai-chat:{settings.openai_chat_model}",
    output_type=CostPlanNarrativeOutput,
    instructions=_load_agent_instructions(),
    defer_model_check=True,
)


def pack_summary_for_narrative(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    lines = [
        f"Project name: {pack.project_name or 'TBC'}",
        f"Owners: {pack.owners or 'TBC'}",
        f"Site: {pack.site_address or 'TBC'}",
        f"Construction budget ceiling (owner brief): {pack.construction_budget_ceiling or 'TBC'}",
        f"Contingency: {pack.contingency_amount or 'TBC'} ({pack.contingency_percent or 'TBC'}%)",
        f"Owner brief on file: {pack.owner_brief_on_file}",
        f"Owner brief signed: {pack.owner_brief_signed_date or 'TBC'}",
        f"Architect fee ex GST: {pack.fee_total_ex_gst or 'TBC'}",
        f"Engagement executed: {mob.engagement_executed_date or 'TBC'}",
        f"Planning pathway memo on file: {pack.planning_memo_on_file}",
        f"Planning pathway: {pack.planning_pathway_summary or mob.planning_pathway or 'TBC'}",
        f"Geotechnical report on file: {not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL)}",
        f"Master programme on file: {not pack_has_gap(pack.mobilisation, GAP_MASTER_PROGRAMME)}",
        f"Principal certifier appointed: {not pack_has_gap(pack.mobilisation, GAP_CERTIFIER)}",
        "Architect fee is outside the construction ceiling — not an overrun of the ceiling.",
        f"Target DA lodgement: {mob.target_da_lodgement or 'TBC'}",
        f"Conflict disclosure: {mob.conflict_disclosure or 'None stated'}",
        f"Builder ROM: {mob.builder_rom or 'none'}",
        f"Builder ROM programme: {mob.builder_rom_programme or 'none'}",
        f"Builder conflict disclosure: {mob.builder_conflict_disclosure or 'none'}",
        "Builder ROM caveats:",
        *[f"- {item}" for item in mob.builder_rom_caveats],
        f"Heritage advice: {mob.heritage_advice or 'none'}",
        f"Heritage context: {mob.heritage_context or 'none'}",
        f"Heritage approval advice: {mob.heritage_approval_advice or 'none'}",
        "Heritage design advice:",
        *[f"- {item}" for item in mob.heritage_design_advice],
        "Owner-supplied items:",
    ]
    if pack.owner_supplied_items:
        for item in pack.owner_supplied_items:
            lines.append(f"- {item.label}: {item.amount_ex_gst or 'TBC'}")
    else:
        lines.append("- none listed")
    lines.append("Gaps:")
    lines.extend(f"- {gap}" for gap in pack.gaps)
    return "\n".join(lines)


def build_cost_plan_narrative_prompt(
    *,
    project: Project,
    pack: CostPlanEvidencePack,
    run_date: date | None = None,
    validation_feedback: str | None = None,
) -> str:
    run_iso = (run_date or date.today()).isoformat()
    parts = [
        f"Project: {project.title}",
        (
            "Overlays: "
            f"archetype={project.archetype}, "
            f"user_role={project.user_role}, "
            f"state={project.state}"
        ),
        (
            f"Cost plan run date: {run_iso} — set due dates 2–4 weeks forward from this date "
            "(ISO YYYY-MM-DD in each recommendation and next step)."
        ),
        "Evidence pack summary:",
        pack_summary_for_narrative(pack),
        f"Evidence refs: {', '.join(pack.evidence_refs) if pack.evidence_refs else 'none'}",
    ]
    if validation_feedback:
        parts.append(
            "REVISION REQUIRED — previous narrative failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate narrative output fixing every issue."
        )
    return "\n\n".join(parts)


def _iso_dates_in_text(text: str) -> list[date]:
    return [date.fromisoformat(match.group(1)) for match in _ISO_DATE_PATTERN.finditer(text)]


def validate_cost_plan_narrative_output(
    output: CostPlanNarrativeOutput,
    pack: CostPlanEvidencePack,
    *,
    run_date: date | None = None,
) -> None:
    issues: list[str] = []
    anchor_date = run_date or date.today()

    if len(output.judgements) < 2:
        issues.append("judgements must include at least 2 items")
    if len(output.recommendations) < 3:
        issues.append("recommendations must include at least 3 items")
    if len(output.risk_rows) < 5:
        issues.append("risk_rows must include at least 5 items")
    if len(output.next_steps) < 3:
        issues.append("next_steps must include at least 3 items")

    for index, row in enumerate(output.risk_rows, start=1):
        if row.owner.strip().lower() in _GENERIC_RISK_OWNERS:
            issues.append(
                f"risk row {index} owner {row.owner!r} is generic — assign a specific "
                "accountable party (Owner, Architect-PM, Structural Engineer, Certifier, Builder)"
            )

    combined = "\n".join(
        [
            *output.judgements,
            *output.recommendations,
            *output.next_steps,
            *[row.risk for row in output.risk_rows],
        ]
    ).lower()

    for phrase in _FORBIDDEN_BUDGET_PHRASES:
        if phrase.lower() in combined and not pack.construction_budget_ceiling:
            issues.append(f"narrative must not invent budget figure ({phrase!r})")

    if pack.construction_budget_ceiling:
        for phrase in ("feasibility study", "$1,500,000", "1,500,000"):
            if phrase.lower() in combined:
                issues.append(
                    f"narrative must use owner brief ceiling, not invented budget ({phrase!r})"
                )
        if re.search(r"\bconfirm budget\b", combined) and not any(
            variant.lower() in combined for variant in _money_variants(pack.construction_budget_ceiling)
        ):
            issues.append(
                "recommendations must reference the evidenced construction ceiling when discussing budget"
            )

    if pack.owner_brief_on_file:
        missing_brief_phrases = (
            "missing owner project brief",
            "owner project brief is missing",
            "obtain formal sign-off on the owner project brief",
            "finalise and obtain formal sign-off on the owner project brief",
        )
        for phrase in missing_brief_phrases:
            if phrase in combined:
                issues.append(
                    f"narrative must not claim owner brief is missing when owner brief is on file ({phrase!r})"
                )

    if pack.construction_budget_ceiling and pack.fee_total_ex_gst:
        for pattern in _FEE_CEILING_MISREAD_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                issues.append(
                    "narrative must treat architect fee as additional to the construction ceiling, "
                    "not exceeding it"
                )
                break

    if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL):
        for phrase in _GEOTECH_COMMISSION_PHRASES:
            if phrase in combined:
                issues.append(
                    f"narrative must not commission geotechnical work when report is on file ({phrase!r})"
                )

    if not pack_has_gap(pack.mobilisation, GAP_MASTER_PROGRAMME):
        for phrase in _MASTER_PROGRAMME_MISSING_PHRASES:
            if phrase in combined:
                issues.append(
                    f"narrative must not ask to create master programme when one is on file ({phrase!r})"
                )

    if not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        if re.search(r"\bappoint (?:a )?principal certifier\b", combined) and "coordinate" not in combined:
            issues.append(
                "narrative must not assign certifier appointment when certifier is already on file"
            )

    for index, recommendation in enumerate(output.recommendations, start=1):
        dates = _iso_dates_in_text(recommendation)
        if not dates:
            issues.append(f"recommendation {index} must include an ISO due date (YYYY-MM-DD)")
            continue
        for due in dates:
            if due < anchor_date:
                issues.append(f"recommendation {index} due date {due} is before cost plan run date")

    for index, step in enumerate(output.next_steps, start=1):
        dates = _iso_dates_in_text(step)
        if not dates:
            issues.append(f"next_steps item {index} must include an ISO due date (YYYY-MM-DD)")

    if issues:
        joined = "; ".join(issues)
        raise WorkflowValidationError(f"Cost plan narrative validation failed: {joined}")


async def run_cost_plan_narrative_model(
    *,
    project: Project,
    pack: CostPlanEvidencePack,
    run_date: date | None = None,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
) -> CostPlanNarrativeOutput:
    prompt = build_cost_plan_narrative_prompt(
        project=project,
        pack=pack,
        run_date=run_date,
        validation_feedback=validation_feedback,
    )
    resolved_model = resolve_chat_model(chat_model)
    result = await run_agent_with_retry(cost_plan_narrative_agent, prompt, model=resolved_model)
    validate_cost_plan_narrative_output(result.output, pack, run_date=run_date)
    return result.output


__all__ = ["CostPlanNarrativeOutput", "format_risk_rows_table", "run_cost_plan_narrative_model"]
