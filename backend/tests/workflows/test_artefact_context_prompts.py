from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.projects.artefact_context import (
    build_cost_plan_context,
    build_pmp_context,
    build_rfp_context,
    build_rft_context,
)
from app.projects.generation_context import (
    ContextField,
    FieldState,
    ProjectGenerationContext,
)
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.rfp_renderer import build_rfp_citation_index
from app.workflows.cost_plan_narrative import build_cost_plan_narrative_prompt
from app.workflows.pmp_narrative import build_pmp_narrative_prompt
from app.workflows.rfp_narrative import (
    build_procurement_narrative_prompt,
    build_rfp_narrative_prompt,
)


def test_bounded_narrative_prompts_use_their_context_lenses() -> None:
    context = _context()
    project = _project()
    citations = build_rfp_citation_index([])

    pmp_prompt = build_pmp_narrative_prompt(
        project=project,
        pack=MobilisationEvidencePack(),
        pmp_context=build_pmp_context(context),
    )
    cost_prompt = build_cost_plan_narrative_prompt(
        project=project,
        pack=CostPlanEvidencePack(mobilisation=MobilisationEvidencePack()),
        cost_plan_context=build_cost_plan_context(context),
    )
    rfp_prompt = build_rfp_narrative_prompt(
        project=project,
        target=SimpleNamespace(
            name="Structural Engineer",
            requested_services=("Develop the structural design.",),
        ),
        rfp_context=build_rfp_context(context, "Structural Engineer"),
        project_evidence=[],
        platform_knowledge=[],
        citation_index=citations,
    )
    rft_prompt = build_procurement_narrative_prompt(
        project=project,
        target_name="Mechanical Services",
        target_label="Procurement package",
        rft_context=build_rft_context(context, "Mechanical Services"),
        baseline_scope=("Provide mechanical services.",),
        project_evidence=[],
        platform_knowledge=[],
        citation_index=citations,
    )

    assert "PMP project context lens" in pmp_prompt
    assert "Cost Plan project context lens" in cost_prompt
    assert "RFP project context lens" in rfp_prompt
    assert "consultant_discipline: Structural Engineer" in rfp_prompt
    assert "RFT project context lens" in rft_prompt
    assert "trade_package: Mechanical Services" in rft_prompt
    assert all(
        "Overlays: archetype=" not in prompt
        for prompt in (pmp_prompt, cost_prompt, rfp_prompt, rft_prompt)
    )
    assert "$5,000,000" not in rfp_prompt
    assert "$5,000,000" not in rft_prompt


def _context() -> ProjectGenerationContext:
    known = FieldState.KNOWN
    unknown = FieldState.UNKNOWN
    return ProjectGenerationContext(
        project_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        context_version=4,
        identity={
            "title": ContextField(
                key="title",
                label="Project title",
                value="Test project",
                state=known,
                source="project",
            ),
            "site_address": ContextField(
                key="site_address",
                label="Site address",
                value="10 Test Street",
                state=known,
                source="project_setup",
            ),
            "client": ContextField(
                key="client",
                label="Client",
                value="Example Client",
                state=known,
                source="project_setup",
            ),
        },
        taxonomy={
            "building_class": _field("building_class", "commercial"),
            "subclasses": _field("subclasses", ["office"]),
            "work_type": _field("work_type", "refurb"),
            "state": _field("state", "NSW"),
            "user_role": _field("user_role", "architect-pm"),
        },
        scale={"nla_sqm": _field("nla_sqm", 4200)},
        complexity={
            "planning": _field("planning", "da"),
            "procurement_route": _field("procurement_route", "traditional"),
            "access_constraints": _field("access_constraints", "urban_constrained"),
        },
        scope={"services_upgrade": _field("services_upgrade", True)},
        commercial={
            "budget": _field("budget", "$5,000,000"),
            "procurement_route": _field("procurement_route", "traditional"),
        },
        programme={
            "phase": _field("phase", "design"),
            "timeframe": ContextField(
                key="timeframe",
                label="Timeframe",
                state=unknown,
            ),
        },
        approvals={"planning_pathway": _field("planning_pathway", "da")},
        stakeholders={"consultants": _field("consultants", ["Structural Engineer"])},
        derived_risks=[],
    )


def _field(key: str, value: object) -> ContextField:
    return ContextField(
        key=key,
        label=key.replace("_", " ").title(),
        value=value,
        state=FieldState.KNOWN,
        source="project_profile",
    )


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        title="Test project",
        archetype="commercial-refurbishment",
        state="NSW",
    )
