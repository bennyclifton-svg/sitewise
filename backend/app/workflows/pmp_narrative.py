"""Bounded LLM narrative slice for hybrid Create PMP (judgements, recommendations, register)."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from app.assistant.pmp_models import resolve_pmp_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.project import Project
from app.projects.artefact_context import PmpContext, format_artefact_context
from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    format_generation_brief,
)
from app.sitewise.mobilisation_evidence import (
    GAP_CONSTRUCTION_BUDGET,
    GAP_MASTER_PROGRAMME,
    GAP_OWNER_BRIEF,
    MobilisationEvidencePack,
    pack_has_gap,
)
from app.sitewise.pmp_evidence_validation import evidence_refs_include_engagement_letter
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.generation_consistency import (
    ConsistencyResolver,
    ConsistencySection,
    format_consistency_failures,
    run_generation_consistency_gate,
)
from app.workflows.generation_consistency_agent import resolve_consistency_candidates
from app.workflows.section_generation import (
    SectionCompletePublisher,
    SectionGenerationJob,
    SectionProgressPublisher,
    run_section_generation,
)

_INSTRUCTIONS_PATH = Path(__file__).with_name("pmp_narrative_instructions.md")
_ISO_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

_NARRATIVE_CONTRADICTIONS: tuple[str, ...] = (
    "no engagement letter found",
    "no engagement letter on file",
    "engagement letter — not yet filed",
    "fee proposal — not yet filed",
    "neither brief filed yet",
    "pre-brief / pre-engagement",
)

_GENERIC_JUDGEMENT_PHRASES: tuple[str, ...] = (
    "on track for",
    "necessitating immediate attention",
    "potential risk to project timelines",
    "ensure that the project's objectives",
    "identified gaps present",
    "immediate attention to ensure",
)

_VAGUE_REGISTER_SOURCES: frozenset[str] = frozenset({"gaps", "gap", "general"})
_ALLOWED_REGISTER_SOURCES: frozenset[str] = frozenset(
    {"engagement letter", "fee proposal"}
)
_CERTIFIER_DA_SCOPE_PHRASES: tuple[str, ...] = (
    "da submission",
    "da submissions",
    "da lodgement",
    "da processing",
    "da approval",
    "processing of da",
)

_ARCHITECT_PM_ACTORS: tuple[str, ...] = (
    "architect-pm",
    "architect pm",
    "architect/ pm",
    "architect to ",
    "hcs ",
    "harrison clarke",
)

_OWNER_ACTORS: tuple[str, ...] = ("owner", "owners")


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _is_architect_actor(text: str) -> bool:
    lowered = text.lower().strip()
    if lowered == "architect" or re.match(r"^architect(?:-pm)?\b", lowered):
        return True
    return _contains_any(lowered, _ARCHITECT_PM_ACTORS)


def _pack_has_gap(pack: MobilisationEvidencePack, needle: str) -> bool:
    return pack_has_gap(pack, needle)


_CLOSED_GAP_ACTION_PHRASES: dict[str, tuple[str, ...]] = {
    GAP_CONSTRUCTION_BUDGET: (
        "confirm budget",
        "budget ceiling",
        "working budget",
        "construction budget",
    ),
    GAP_OWNER_BRIEF: (
        "brief sign-off",
        "brief sign off",
        "sign-off on the owner project brief",
        "sign off on the owner project brief",
        "owner project brief sign",
    ),
}


def _validate_no_actions_for_closed_gaps(
    output: PmpNarrativeOutput,
    pack: MobilisationEvidencePack,
    issues: list[str],
) -> None:
    combined = "\n".join(
        [
            *output.recommendations,
            *[row.description for row in output.register_rows],
            *[row.next_action for row in output.register_rows],
        ]
    ).lower()

    for gap_label, phrases in _CLOSED_GAP_ACTION_PHRASES.items():
        if pack_has_gap(pack, gap_label):
            continue
        for phrase in phrases:
            if phrase in combined:
                issues.append(
                    f"narrative must not request {gap_label!r} actions — gap is closed in evidence pack"
                )
                break


def _recommendation_assigns_certifier_to_architect_pm(recommendation: str) -> bool:
    lowered = recommendation.lower()
    if "certifier" not in lowered:
        return False
    if not _is_architect_actor(lowered):
        return False
    return any(
        verb in lowered for verb in ("appoint", "engage", "secure", "select", "procure")
    )


def _register_row_assigns_certifier_to_architect_pm(row: RegisterRow) -> bool:
    lowered = f"{row.description} {row.next_action} {row.owner}".lower()
    if "certifier" not in lowered:
        return False
    return _is_architect_actor(row.owner) and any(
        verb in lowered for verb in ("appoint", "engage", "secure", "select")
    )


def _certifier_text_misstates_da_scope(text: str) -> bool:
    lowered = text.lower()
    return "certifier" in lowered and _contains_any(
        lowered, _CERTIFIER_DA_SCOPE_PHRASES
    )


def _repair_certifier_da_scope_text(text: str) -> str:
    if not _certifier_text_misstates_da_scope(text):
        return text
    repaired = re.sub(
        r"\s+to ensure compliance and timely processing of DA submissions\.?",
        " to support the construction certificate pathway.",
        text,
        flags=re.IGNORECASE,
    )
    for phrase in _CERTIFIER_DA_SCOPE_PHRASES:
        repaired = re.sub(
            re.escape(phrase),
            "construction certificate pathway",
            repaired,
            flags=re.IGNORECASE,
        )
    return repaired


def _register_source_is_allowed(source: str) -> bool:
    lowered = source.strip().lower()
    return lowered in _ALLOWED_REGISTER_SOURCES or lowered.startswith("gap:")


def _combined_register_text(output: PmpNarrativeOutput) -> str:
    return "\n".join(
        f"{row.description} {row.source} {row.next_action}"
        for row in output.register_rows
    ).lower()


def _default_due_date(run_date: date | None) -> str:
    anchor = run_date or date.today()
    return (anchor + timedelta(days=21)).isoformat()


def _next_register_id(rows: list[RegisterRow]) -> str:
    used = {row.id.strip().lower() for row in rows}
    for index in range(1, 1000):
        candidate = f"R-{index:03d}"
        if candidate.lower() not in used:
            return candidate
    raise ValueError("Unable to allocate PMP register row id")


def _programme_action_text(pack: MobilisationEvidencePack, due_date: str) -> str:
    if pack.target_da_lodgement:
        return (
            "Architect to issue master programme aligned to "
            f"{pack.target_da_lodgement} DA target by {due_date}."
        )
    return f"Architect to issue master programme closing the open programme gap by {due_date}."


def complete_pack_driven_narrative_requirements(
    output: PmpNarrativeOutput,
    pack: MobilisationEvidencePack,
    *,
    run_date: date | None = None,
) -> PmpNarrativeOutput:
    """Add deterministic pack-required audit actions before strict validation."""
    recommendations = list(output.recommendations)
    register_rows = list(output.register_rows)
    due_date = _default_due_date(run_date)

    def recommendations_text() -> str:
        return "\n".join(recommendations).lower()

    def register_text() -> str:
        return "\n".join(
            f"{row.description} {row.source} {row.next_action}" for row in register_rows
        ).lower()

    if pack.target_da_lodgement or _pack_has_gap(pack, GAP_MASTER_PROGRAMME):
        if "program" not in recommendations_text():
            recommendations.append(_programme_action_text(pack, due_date))
        if "program" not in register_text():
            source = (
                "engagement letter"
                if pack.target_da_lodgement
                else f"gap: {GAP_MASTER_PROGRAMME}"
            )
            next_action = (
                f"Issue programme aligned to {pack.target_da_lodgement} DA target"
                if pack.target_da_lodgement
                else "Issue master programme"
            )
            register_rows.insert(
                0,
                RegisterRow(
                    id=_next_register_id(register_rows),
                    description="Master programme",
                    owner="Architect",
                    status="Open",
                    due_date=due_date,
                    source=source,
                    next_action=next_action,
                ),
            )

    if pack.conflict_disclosure:
        conflict_tokens = ("conflict", "linden", "declaration")
        if not _contains_any(recommendations_text(), conflict_tokens):
            recommendations.append(
                "Architect to declare disclosed tender conflict before tender list lock "
                f"by {due_date}."
            )
        if not _contains_any(register_text(), conflict_tokens):
            register_rows.append(
                RegisterRow(
                    id=_next_register_id(register_rows),
                    description="Tender conflict declaration",
                    owner="Architect",
                    status="Open",
                    due_date=due_date,
                    source="fee proposal",
                    next_action="Declare disclosed tender conflict before tender list lock",
                )
            )

    if _pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET):
        if not (
            _contains_any(recommendations_text(), _OWNER_ACTORS)
            and "budget" in recommendations_text()
        ):
            recommendations.append(
                f"Owner to confirm construction budget allowance by {due_date}."
            )
        if "budget" not in register_text():
            register_rows.append(
                RegisterRow(
                    id=_next_register_id(register_rows),
                    description="Working budget ceiling",
                    owner="Owner",
                    status="Open",
                    due_date=due_date,
                    source=f"gap: {GAP_CONSTRUCTION_BUDGET}",
                    next_action="Confirm construction budget allowance",
                )
            )

    conflict_tokens = ("conflict", "linden", "declaration")
    repaired_rows: list[RegisterRow] = []
    for row in register_rows:
        row_text = f"{row.description} {row.source} {row.next_action}"
        source = row.source
        if pack.conflict_disclosure and _contains_any(row_text, conflict_tokens):
            source = "fee proposal"
        repaired_rows.append(
            row.model_copy(
                update={
                    "source": source,
                    "description": _repair_certifier_da_scope_text(row.description),
                    "next_action": _repair_certifier_da_scope_text(row.next_action),
                }
            )
        )

    return output.model_copy(
        update={
            "recommendations": [
                _repair_certifier_da_scope_text(item) for item in recommendations
            ],
            "register_rows": repaired_rows,
        }
    )


def _validate_pack_driven_narrative_requirements(
    output: PmpNarrativeOutput,
    pack: MobilisationEvidencePack,
    issues: list[str],
) -> None:
    register_text = _combined_register_text(output)
    recommendations_text = "\n".join(output.recommendations).lower()
    judgements_text = "\n".join(output.judgements).lower()

    if pack.target_da_lodgement or _pack_has_gap(pack, "master programme"):
        if "program" not in register_text:
            issues.append(
                "register_rows must include a master programme row when a DA target or "
                "master programme gap exists"
            )
        if "program" not in recommendations_text:
            issues.append(
                "recommendations must include a master programme action when a DA target "
                "or master programme gap exists"
            )

    if pack.conflict_disclosure:
        conflict_tokens = ("conflict", "linden", "declaration")
        if not _contains_any(register_text, conflict_tokens):
            issues.append(
                "register_rows must include a conflict declaration row when fee proposal "
                "discloses a tender conflict"
            )
        if not _contains_any(recommendations_text, conflict_tokens):
            issues.append(
                "recommendations must include a conflict declaration action when fee "
                "proposal discloses a tender conflict"
            )

    if _pack_has_gap(pack, "construction budget"):
        if "budget" not in register_text:
            issues.append(
                "register_rows must include a construction budget row when budget is a gap"
            )
        if not (
            _contains_any(recommendations_text, _OWNER_ACTORS)
            and "budget" in recommendations_text
        ):
            issues.append(
                "recommendations must include an Owner budget confirmation action when "
                "construction budget is a gap"
            )

    if pack.planning_pathway and not _contains_any(
        judgements_text,
        ("pathway", "cdc", " da ", "da/"),
    ):
        issues.append(
            "judgements must reference the planning pathway (DA/CDC) when stated in the evidence pack"
        )

    if pack.target_da_lodgement and not _contains_any(
        judgements_text,
        ("september", "programme", "program", "da target", "lodgement"),
    ):
        issues.append(
            "judgements must reference the DA programme target when stated in the evidence pack"
        )

    for index, judgement in enumerate(output.judgements, start=1):
        if _contains_any(judgement, _GENERIC_JUDGEMENT_PHRASES):
            issues.append(
                f"judgement {index} uses generic filler phrasing; cite evidence-specific posture"
            )

    for index, recommendation in enumerate(output.recommendations, start=1):
        if _recommendation_assigns_certifier_to_architect_pm(recommendation):
            issues.append(
                f"recommendation {index} assigns certifier appointment to Architect; "
                "Owner appoints the principal certifier"
            )
        if _certifier_text_misstates_da_scope(recommendation):
            issues.append(
                f"recommendation {index} ties certifier appointment to DA lodgement/submission; "
                "principal certifier belongs to the CC/construction certification pathway"
            )

    for row in output.register_rows:
        if _register_row_assigns_certifier_to_architect_pm(row):
            issues.append(
                f"register row {row.id} assigns certifier appointment to Architect; "
                "Owner appoints the principal certifier"
            )
        source = row.source.strip().lower()
        if source in _VAGUE_REGISTER_SOURCES:
            issues.append(
                f"register row {row.id} source {row.source!r} is too vague; cite engagement "
                "letter, fee proposal, or gap: <name>"
            )
        elif not _register_source_is_allowed(source):
            issues.append(
                f"register row {row.id} source {row.source!r} must cite engagement letter, "
                "fee proposal, or gap: <name>"
            )
        if _certifier_text_misstates_da_scope(f"{row.description} {row.next_action}"):
            issues.append(
                f"register row {row.id} ties certifier appointment to DA lodgement/submission; "
                "principal certifier belongs to the CC/construction certification pathway"
            )

    _validate_no_actions_for_closed_gaps(output, pack, issues)


class RegisterRow(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=512)
    owner: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=64)
    due_date: str = Field(min_length=10, max_length=10)
    source: str = Field(min_length=1, max_length=256)
    next_action: str = Field(min_length=1, max_length=512)

    @field_validator("due_date")
    @classmethod
    def validate_iso_due_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class RiskRow(BaseModel):
    risk: str = Field(min_length=1, max_length=512)
    owner: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=64)
    next_action: str = Field(min_length=1, max_length=512)
    due_date: str = Field(min_length=1, max_length=32)


class PmpNarrativeOutput(BaseModel):
    judgements: list[str] = Field(min_length=2)
    recommendations: list[str] = Field(min_length=3)
    register_rows: list[RegisterRow] = Field(min_length=1)
    risk_rows: list[RiskRow] = Field(default_factory=list)
    workflow_warnings: list[str] = Field(default_factory=list)
    consistency_ai_call_count: int = Field(default=0, ge=0, exclude=True)


class PmpAssessmentOutput(BaseModel):
    judgements: list[str] = Field(min_length=2)
    workflow_warnings: list[str] = Field(default_factory=list)


class PmpActionsOutput(BaseModel):
    recommendations: list[str] = Field(min_length=3)
    register_rows: list[RegisterRow] = Field(min_length=1)


class PmpRisksOutput(BaseModel):
    risk_rows: list[RiskRow] = Field(default_factory=list)


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


_assessment_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=PmpAssessmentOutput,
    instructions=(
        _load_agent_instructions()
        + "\nReturn only evidence-specific judgements and workflow warnings."
    ),
    defer_model_check=True,
)
_actions_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=PmpActionsOutput,
    instructions=(
        _load_agent_instructions()
        + "\nReturn only dated recommendations and the action register rows."
    ),
    defer_model_check=True,
)
_risks_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=PmpRisksOutput,
    instructions=(
        _load_agent_instructions()
        + "\nReturn only the concise project risk register rows."
    ),
    defer_model_check=True,
)


def pack_summary_for_narrative(pack: MobilisationEvidencePack) -> str:
    """Compact bullet summary of pack facts for a small narrative prompt."""
    lines = [
        f"Owners: {pack.owners or 'TBC'}",
        f"Site: {pack.site_address or 'TBC'}",
        f"Dwelling: {pack.dwelling_summary or 'TBC'}",
        f"Engagement executed: {pack.engagement_executed_date or 'TBC'}",
        f"Appointee: {pack.appointee or 'TBC'}",
        f"Fee total ex GST: {pack.fee_total_ex_gst or 'TBC'}",
        f"Planning pathway: {pack.planning_pathway or 'TBC'}",
        f"Target DA lodgement: {pack.target_da_lodgement or 'TBC'}",
        f"PI: {pack.pi_insurer or 'TBC'} / {pack.pi_limit or 'TBC'} (holder {pack.pi_holder or 'TBC'})",
        f"Procurement: {pack.invited_builder_count or 'TBC'} invited builders; "
        f"{pack.formal_tender_count or 'TBC'} formal tender; CA {pack.ca_months_assumed or 'TBC'} months",
        f"Conflict disclosure: {pack.conflict_disclosure or 'None stated'}",
    ]
    if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF):
        signed = pack.owner_brief_signed_date or "on file"
        lines.append(
            f"Owner project brief: signed {signed} — do NOT recommend brief sign-off."
        )
    if pack.construction_budget_ceiling and not pack_has_gap(
        pack, GAP_CONSTRUCTION_BUDGET
    ):
        lines.append(
            f"Construction budget confirmed: {pack.construction_budget_ceiling} working ceiling — "
            "do NOT recommend budget confirmation."
        )
    if pack.builder_quotes:
        lines.append(
            "Builder quotes on file (unverified market pricing — a pricing signal, never the "
            "owner budget; quote exclusions are latent-condition risks to carry):"
        )
        lines.extend(f"- {quote}" for quote in pack.builder_quotes)
    if pack.other_evidence:
        lines.append(
            "Other indexed evidence (unclassified — acknowledge, do not invent detail):"
        )
        lines.extend(f"- {item}" for item in pack.other_evidence)
    lines.append("Open gaps (address these only):")
    if pack.gaps:
        lines.extend(f"- {gap}" for gap in pack.gaps)
    else:
        lines.append("- None identified.")
    return "\n".join(lines)


def build_pmp_narrative_prompt(
    *,
    project: Project,
    pack: MobilisationEvidencePack,
    pmp_context: PmpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    run_date: date | None = None,
    validation_feedback: str | None = None,
) -> str:
    """Build a small narrative-only prompt — no doctrine or seed paste."""
    mobilisation_date = (run_date or date.today()).isoformat()
    parts = [
        f"Project: {project.title}",
        *(
            [format_generation_brief(generation_brief)]
            if generation_brief is not None
            else [format_artefact_context(pmp_context)]
            if pmp_context is not None
            else [f"Overlays: archetype={project.archetype}, state={project.state}"]
        ),
        (
            f"Mobilisation run date: {mobilisation_date} — set register due dates and "
            "recommendation due dates 2–4 weeks forward from this date."
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
    return [
        date.fromisoformat(match.group(1)) for match in _ISO_DATE_PATTERN.finditer(text)
    ]


def validate_pmp_narrative_output(
    output: PmpNarrativeOutput,
    pack: MobilisationEvidencePack,
    *,
    run_date: date | None = None,
) -> None:
    """Validate narrative slice against hybrid contract and evidence pack."""
    issues: list[str] = []
    anchor_date = run_date or date.today()
    earliest_due = anchor_date
    latest_due = anchor_date + timedelta(days=28)

    if len(output.judgements) < 2:
        issues.append("judgements must include at least 2 items")

    if len(output.recommendations) < 3:
        issues.append("recommendations must include at least 3 items")

    for index, recommendation in enumerate(output.recommendations, start=1):
        dates = _iso_dates_in_text(recommendation)
        if not dates:
            issues.append(
                f"recommendation {index} must include an ISO due date (YYYY-MM-DD)"
            )
            continue
        for due in dates:
            if due < anchor_date:
                issues.append(
                    f"recommendation {index} due date {due} is before mobilisation run date"
                )

    if len(output.register_rows) < 1:
        issues.append("register_rows must include at least 1 row")

    for row in output.register_rows:
        due = date.fromisoformat(row.due_date)
        if due < earliest_due:
            issues.append(
                f"register row {row.id} due date {row.due_date} is before mobilisation run date"
            )
        if due > latest_due + timedelta(days=14):
            issues.append(
                f"register row {row.id} due date {row.due_date} is more than ~6 weeks after run date"
            )

    combined = "\n".join(
        [
            *output.judgements,
            *output.recommendations,
            *[row.description for row in output.register_rows],
            *[row.next_action for row in output.register_rows],
            *output.workflow_warnings,
        ]
    ).lower()

    if evidence_refs_include_engagement_letter(pack.evidence_refs):
        for phrase in _NARRATIVE_CONTRADICTIONS:
            if phrase in combined:
                issues.append(
                    f"narrative contradiction: {phrase!r} conflicts with evidence on file"
                )

    for warning in output.workflow_warnings:
        lowered = warning.lower()
        if "engagement letter" in lowered and any(
            token in lowered
            for token in ("missing", "not on file", "not yet", "no engagement")
        ):
            issues.append(
                "workflow_warnings must not claim engagement letter is missing"
            )

    _validate_pack_driven_narrative_requirements(output, pack, issues)

    if issues:
        joined = "; ".join(issues)
        raise WorkflowValidationError(f"PMP narrative validation failed: {joined}")


def format_register_rows_table(rows: list[RegisterRow]) -> str:
    header = (
        "| ID | Description | Owner | Status | Due date | Source | Next action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    )
    body = [
        f"| {row.id} | {row.description} | {row.owner} | {row.status} | "
        f"{row.due_date} | {row.source} | {row.next_action} |"
        for row in rows
    ]
    return "\n".join([*header, *body])


def format_risk_rows_table(rows: list[RiskRow]) -> str:
    header = (
        "| Risk | Owner | Status | Next action | Due |",
        "| --- | --- | --- | --- | --- |",
    )
    body = [
        f"| {row.risk} | {row.owner} | {row.status} | {row.next_action} | {row.due_date} |"
        for row in rows
    ]
    return "\n".join([*header, *body])


def format_internal_audit_narrative(output: PmpNarrativeOutput) -> str:
    """Render review-only narrative fragments without duplicating issued registers."""
    lines = [
        "- **Judgements**",
        *[f"  - {item}" for item in output.judgements],
        "- **Workflow warnings**",
    ]
    if output.workflow_warnings:
        lines.extend(f"  - {item}" for item in output.workflow_warnings)
    else:
        lines.append("  - None.")
    return "\n".join(lines)


async def run_pmp_narrative_model(
    *,
    project: Project,
    pack: MobilisationEvidencePack,
    pmp_context: PmpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    run_date: date | None = None,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
    on_progress: SectionProgressPublisher | None = None,
    on_section_complete: SectionCompletePublisher | None = None,
    consistency_resolver: ConsistencyResolver | None = None,
) -> PmpNarrativeOutput:
    """Generate independent PMP narrative slices with bounded concurrency."""
    prompt = build_pmp_narrative_prompt(
        project=project,
        pack=pack,
        pmp_context=pmp_context,
        generation_brief=generation_brief,
        run_date=run_date,
        validation_feedback=validation_feedback,
    )
    resolved_model = (
        chat_model.strip() if chat_model else resolve_pmp_model().execution_id
    )

    async def run_section(agent: Agent, instruction: str):
        return await run_agent_with_retry(
            agent,
            f"{prompt}\n\nSECTION JOB:\n{instruction}",
            model=resolved_model,
        )

    results = await run_section_generation(
        (
            SectionGenerationJob(
                key="assessment",
                label="Judgements and warnings",
                run=lambda: run_section(
                    _assessment_agent,
                    "Produce the evidence-specific assessment only.",
                ),
            ),
            SectionGenerationJob(
                key="actions",
                label="Recommendations and action register",
                run=lambda: run_section(
                    _actions_agent,
                    "Produce dated recommendations and action register rows only.",
                ),
            ),
            SectionGenerationJob(
                key="risks",
                label="Risk register",
                run=lambda: run_section(
                    _risks_agent,
                    "Produce the risk register rows only.",
                ),
            ),
        ),
        max_concurrency=3,
        on_progress=on_progress,
        on_section_complete=on_section_complete,
    )
    assessment = results["assessment"].output
    actions = results["actions"].output
    risks = results["risks"].output
    combined = PmpNarrativeOutput(
        judgements=assessment.judgements,
        workflow_warnings=assessment.workflow_warnings,
        recommendations=actions.recommendations,
        register_rows=actions.register_rows,
        risk_rows=risks.risk_rows,
    )
    output = complete_pack_driven_narrative_requirements(
        combined,
        pack,
        run_date=run_date,
    )
    if generation_brief is not None:
        report = await run_generation_consistency_gate(
            generation_brief,
            (
                ConsistencySection(
                    key="assessment",
                    text=_consistency_lines(
                        *output.judgements,
                        *output.workflow_warnings,
                    ),
                ),
                ConsistencySection(
                    key="actions",
                    text=_consistency_lines(
                        *output.recommendations,
                        *(
                            value
                            for row in output.register_rows
                            for value in row.model_dump(mode="json").values()
                        ),
                    ),
                    scope_items=tuple(output.recommendations),
                ),
                ConsistencySection(
                    key="risks",
                    text=_consistency_lines(
                        *(
                            value
                            for row in output.risk_rows
                            for value in row.model_dump(mode="json").values()
                        ),
                    ),
                    risk_items=tuple(row.risk for row in output.risk_rows),
                ),
            ),
            run_date=run_date,
            resolver=consistency_resolver or resolve_consistency_candidates,
        )
        if not report.is_consistent:
            raise WorkflowValidationError(
                "PMP narrative consistency failed: "
                + format_consistency_failures(report),
                consistency_ai_call_count=report.ai_call_count,
            )
        output = output.model_copy(
            update={"consistency_ai_call_count": report.ai_call_count}
        )
    try:
        validate_pmp_narrative_output(output, pack, run_date=run_date)
    except WorkflowValidationError as exc:
        exc.consistency_ai_call_count += output.consistency_ai_call_count
        raise
    return output


def _consistency_lines(*values: object) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for value in values
        for line in str(value).splitlines()
        if line.strip()
    )
