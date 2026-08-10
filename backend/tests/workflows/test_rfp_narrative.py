from datetime import date
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.projects.artefact_context import RfpContext
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ContextField, FieldState
from app.sitewise.rfp_renderer import build_rfp_citation_index
from app.workflows.consultant_procurement import normalise_discipline
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.rfp_narrative import (
    build_rfp_narrative_prompt,
    run_rfp_narrative_model,
)
from tests.conftest import run_async


def _generation_brief():
    def known(key: str, value: object) -> ContextField:
        return ContextField(
            key=key,
            label=key.replace("_", " ").title(),
            value=value,
            state=FieldState.KNOWN,
            source="project",
        )

    return build_generation_brief(
        RfpContext(
            project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            context_version=7,
            discipline="Structural Engineer",
            identity={"title": known("title", "Walsh Renovation")},
            taxonomy={},
            scope={},
            scale={},
            complexity={},
            programme={},
            procurement={},
            approvals={},
            stakeholders={},
            derived_risks=[],
            section_weights={},
            critical_unknowns=[],
        )
    )


def _section_results(
    *,
    background: str = "Project: Walsh Renovation",
    requested_services: list[str] | None = None,
    programme: list[str] | None = None,
) -> dict:
    return {
        "background": SimpleNamespace(
            output=SimpleNamespace(background=background, evidence_refs=[])
        ),
        "requested_services": SimpleNamespace(
            output=SimpleNamespace(
                requested_services=requested_services
                or [
                    "Develop the structural design and coordinate documented interfaces."
                ],
                evidence_refs=[],
            )
        ),
        "programme": SimpleNamespace(
            output=SimpleNamespace(
                programme=programme
                or ["Submit the proposal in accordance with the RFP timetable."],
                evidence_refs=[],
            )
        ),
    }


def test_rfp_combined_sections_pass_consistency_without_extra_model_call() -> None:
    resolver = AsyncMock(return_value=set())
    with patch(
        "app.workflows.rfp_narrative.run_section_generation",
        new=AsyncMock(return_value=_section_results()),
    ):
        output = run_async(
            run_rfp_narrative_model(
                project=SimpleNamespace(title="Walsh Renovation"),
                target=normalise_discipline("structural engineer"),
                generation_brief=_generation_brief(),
                project_evidence=[],
                platform_knowledge=[],
                citation_index=build_rfp_citation_index([]),
                consistency_resolver=resolver,
            )
        )

    assert output.consistency_ai_call_count == 0
    resolver.assert_not_awaited()


def test_rfp_combined_sections_reject_consultant_name_conflict() -> None:
    resolver = AsyncMock(return_value=set())
    with (
        patch(
            "app.workflows.rfp_narrative.run_section_generation",
            new=AsyncMock(
                return_value=_section_results(
                    background="Consultant discipline: Town Planner"
                )
            ),
        ),
        pytest.raises(WorkflowValidationError, match="Town Planner"),
    ):
        run_async(
            run_rfp_narrative_model(
                project=SimpleNamespace(title="Walsh Renovation"),
                target=normalise_discipline("structural engineer"),
                generation_brief=_generation_brief(),
                project_evidence=[],
                platform_knowledge=[],
                citation_index=build_rfp_citation_index([]),
                consistency_resolver=resolver,
            )
        )

    resolver.assert_not_awaited()


def test_rfp_combined_sections_reject_past_due_date() -> None:
    resolver = AsyncMock(return_value=set())
    with (
        patch(
            "app.workflows.rfp_narrative.run_section_generation",
            new=AsyncMock(
                return_value=_section_results(programme=["Proposal due 2026-08-09."])
            ),
        ),
        pytest.raises(WorkflowValidationError, match="before generation date"),
    ):
        run_async(
            run_rfp_narrative_model(
                project=SimpleNamespace(title="Walsh Renovation"),
                target=normalise_discipline("structural engineer"),
                generation_brief=_generation_brief(),
                project_evidence=[],
                platform_knowledge=[],
                citation_index=build_rfp_citation_index([]),
                run_date=date(2026, 8, 10),
                consistency_resolver=resolver,
            )
        )

    resolver.assert_not_awaited()


def test_rfp_consistency_conflict_publishes_and_carries_ai_call_count() -> None:
    progress = AsyncMock()

    async def confirm_first_candidate(brief, candidates):
        del brief
        return {candidates[0].id}

    with (
        patch(
            "app.workflows.rfp_narrative.run_section_generation",
            new=AsyncMock(
                return_value=_section_results(
                    requested_services=[
                        "Review the structural design basis, existing conditions, footing capacity and loads.",
                        "Review the structural design basis, existing conditions, seismic capacity and loads.",
                    ]
                )
            ),
        ),
        pytest.raises(WorkflowValidationError) as raised,
    ):
        run_async(
            run_rfp_narrative_model(
                project=SimpleNamespace(title="Walsh Renovation"),
                target=normalise_discipline("structural engineer"),
                generation_brief=_generation_brief(),
                project_evidence=[],
                platform_knowledge=[],
                citation_index=build_rfp_citation_index([]),
                on_progress=progress,
                consistency_resolver=confirm_first_candidate,
            )
        )

    assert raised.value.consistency_ai_call_count == 1
    assert progress.await_args_list[-1].args[0] == {
        "stage": "consistency_complete",
        "ai_call_count": 1,
    }


def test_rfp_narrative_prompt_pairs_each_evidence_snippet_with_its_token() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/03-design/site-plan.pdf",
            "filename": "site-plan.pdf",
            "snippet": "The proposed work retains the existing northern wall.",
        },
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
            "snippet": "The owners propose a two-storey rear addition.",
        },
    ]
    citation_index = build_rfp_citation_index(evidence)

    prompt = build_rfp_narrative_prompt(
        project=SimpleNamespace(title="Walsh Renovation"),
        target=normalise_discipline("town planner"),
        project_evidence=evidence,
        platform_knowledge=[
            {
                "title": "Procurement guide",
                "snippet": "Request staged fees and explicit exclusions.",
            }
        ],
        citation_index=citation_index,
    )

    for item in evidence:
        token = citation_index.token_for(item["relative_path"])
        assert f"{token} {item['filename']}: {item['snippet']}" in prompt
    assert "Platform knowledge (guidance only, not project evidence):" in prompt
    assert prompt.index("Platform knowledge") < prompt.index("Project evidence")
    assert "PPR/project brief for overarching project intent" in prompt


def test_rfp_narrative_prompt_prioritises_project_specific_requested_services() -> None:
    project = SimpleNamespace(
        title="Industrial",
        state="NSW",
        building_class="industrial",
        work_type="extend",
        project_metadata={
            "taxonomy": {
                "subclasses": ["warehouse"],
                "scale": {"gfa_sqm": 2135, "office_percent": 9.3},
            }
        },
    )
    target = normalise_discipline("mechanical engineer")
    evidence = [
        {
            "relative_path": "docs/design-brief.pdf",
            "filename": "design-brief.pdf",
            "snippet": (
                "Warehouse mechanical services include MHE charging ventilation "
                "and smoke clearance."
            ),
        }
    ]
    citation_index = build_rfp_citation_index(evidence)

    prompt = build_rfp_narrative_prompt(
        project=project,
        target=target,
        project_evidence=evidence,
        platform_knowledge=[],
        citation_index=citation_index,
    )

    assert "Project profile:" in prompt
    assert "industrial / extend / warehouse / 2135 m² GFA" in prompt
    assert "Relevant taxonomy emphasis:" in prompt
    assert "scope-client-requirements=" in prompt
    assert "Requested services is the highest-priority RFP section" in prompt
    assert "Baseline requested services to tailor" in prompt
    assert target.requested_services[0] in prompt
    assert "Programme narrative slots" in prompt
