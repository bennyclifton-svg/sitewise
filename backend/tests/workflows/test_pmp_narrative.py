import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.sitewise.mobilisation_evidence import extract_mobilisation_evidence_pack
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.pmp_narrative import (
    PmpNarrativeOutput,
    RegisterRow,
    RiskRow,
    build_pmp_narrative_prompt,
    format_internal_audit_narrative,
    format_register_rows_table,
    pack_summary_for_narrative,
    run_pmp_narrative_model,
    validate_pmp_narrative_output,
)
from tests.conftest import run_async

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "chen-residence"
ENGAGEMENT_FIXTURE = FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md"
FEE_FIXTURE = FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md"

ENGAGEMENT_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "01-engagement-letter-harrison-clarke-studio.md#chunk=abc"
)
FEE_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "02-fee-proposal-harrison-clarke-studio.md#chunk=def"
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
RUN_DATE = date(2026, 6, 8)


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="test-project-112",
        title="Chen Residence",
        workspace_path="04-projects/test-project-112",
        phase="brief-planning",
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata=None,
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )


def _pack():
    source_texts = [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]
    return extract_mobilisation_evidence_pack(source_texts, [ENGAGEMENT_REF, FEE_REF])


def _chen_stage1_source_texts() -> list[str]:
    return [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
        (FIXTURE_DIR / "03-owner-project-brief-chen-residence.md").read_text(encoding="utf-8"),
        (FIXTURE_DIR / "04-email-thread-brief-signoff.md").read_text(encoding="utf-8"),
    ]


def _valid_harrison_clarke_narrative() -> PmpNarrativeOutput:
    return PmpNarrativeOutput(
        judgements=[
            "Post-engagement mobilisation posture; master programme required before September 2026 DA target.",
            "DA pathway assumed (not CDC) per fee proposal — programme contingent on due diligence completion.",
        ],
        recommendations=[
            "Owner to confirm working budget ceiling by 2026-06-28.",
            "Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.",
            "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
        ],
        register_rows=[
            RegisterRow(
                id="R-001",
                description="Master programme",
                owner="Architect-PM",
                status="Open",
                due_date="2026-06-28",
                source="engagement letter",
                next_action="Issue programme aligned to September 2026 DA target",
            ),
            RegisterRow(
                id="R-002",
                description="Linden conflict declaration",
                owner="Architect-PM",
                status="Open",
                due_date="2026-06-28",
                source="fee proposal",
                next_action="Declare evaluation involvement before tender list lock",
            ),
            RegisterRow(
                id="R-003",
                description="Working budget ceiling",
                owner="Owner",
                status="Open",
                due_date="2026-06-28",
                source="gap: construction budget",
                next_action="Confirm construction budget allowance",
            ),
        ],
        risk_rows=[
            RiskRow(
                risk="Planning pathway / DA programme slip",
                owner="Owner",
                status="Assumption",
                next_action="Confirm DA pathway and September 2026 lodgement target",
                due_date="2026-06-28",
            ),
        ],
        workflow_warnings=[
            "Geotechnical report not on file.",
            "Certifier not yet appointed.",
        ],
    )


def test_build_pmp_narrative_prompt_is_compact_and_evidence_only() -> None:
    pack = _pack()
    prompt = build_pmp_narrative_prompt(project=_project(), pack=pack, run_date=RUN_DATE)

    assert "Evidence pack summary:" in prompt
    assert "Michael and Sarah Chen" in prompt
    assert "September 2026" in prompt
    assert "Greenfield content contract" not in prompt
    assert "docs/clerk-brief.md" not in prompt
    assert len(prompt) < 4000


def test_pack_summary_for_narrative_lists_gaps() -> None:
    summary = pack_summary_for_narrative(_pack())

    assert "Geotechnical report" in summary
    assert "148,500" in summary


def test_validate_pmp_narrative_output_accepts_harrison_clarke_fixture() -> None:
    validate_pmp_narrative_output(
        _valid_harrison_clarke_narrative(),
        _pack(),
        run_date=RUN_DATE,
    )


def test_validate_pmp_narrative_output_rejects_missing_recommendation_dates() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "recommendations": [
                "Owner to confirm budget soon.",
                "Architect-PM to issue programme.",
                "Architect-PM to declare conflict.",
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="ISO due date"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_engagement_contradiction() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={"workflow_warnings": ["No engagement letter on file."]}
    )
    with pytest.raises(WorkflowValidationError, match="contradiction"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_generic_judgements() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "judgements": [
                "The project is on track for a target DA lodgement in September 2026.",
                "Identified gaps present a potential risk to project timelines.",
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="generic filler"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_architect_pm_certifier_appointment() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "recommendations": [
                "Owner to confirm working budget ceiling by 2026-06-28.",
                "Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.",
                "Architect-PM must appoint a certifier and commission geotechnical report by 2026-06-22.",
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="certifier appointment"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_certifier_da_scope() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "recommendations": [
                "Owner to appoint a principal certifier by 2026-06-28 to support DA submissions.",
                "Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.",
                "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="DA lodgement/submission"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_requires_master_programme_register_row() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "register_rows": [
                RegisterRow(
                    id="R-002",
                    description="Linden conflict declaration",
                    owner="Architect-PM",
                    status="Open",
                    due_date="2026-06-28",
                    source="fee proposal",
                    next_action="Declare evaluation involvement before tender list lock",
                ),
                RegisterRow(
                    id="R-003",
                    description="Working budget ceiling",
                    owner="Owner",
                    status="Open",
                    due_date="2026-06-28",
                    source="gap: construction budget",
                    next_action="Confirm construction budget allowance",
                ),
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="master programme row"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_vague_register_source() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "register_rows": [
                RegisterRow(
                    id="001",
                    description="Obtain formal sign-off on the owner project brief.",
                    owner="Architect-PM",
                    status="Open",
                    due_date="2026-06-28",
                    source="gaps",
                    next_action="Reach out to owners for brief review and sign-off.",
                ),
                *_valid_harrison_clarke_narrative().register_rows[1:],
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="too vague"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_invalid_register_source() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "register_rows": [
                _valid_harrison_clarke_narrative().register_rows[0],
                RegisterRow(
                    id="R-002",
                    description="Linden conflict declaration",
                    owner="Architect-PM",
                    status="Open",
                    due_date="2026-06-28",
                    source="conflict disclosure",
                    next_action="Declare evaluation involvement before tender list lock",
                ),
                _valid_harrison_clarke_narrative().register_rows[2],
            ]
        }
    )
    with pytest.raises(WorkflowValidationError, match="must cite engagement letter"):
        validate_pmp_narrative_output(narrative, _pack(), run_date=RUN_DATE)


def test_validate_pmp_narrative_output_rejects_actions_for_closed_budget_gap() -> None:
    pack = extract_mobilisation_evidence_pack(_chen_stage1_source_texts(), [ENGAGEMENT_REF, FEE_REF])
    narrative = _valid_harrison_clarke_narrative()
    with pytest.raises(WorkflowValidationError, match="Construction budget"):
        validate_pmp_narrative_output(narrative, pack, run_date=RUN_DATE)


def test_pack_summary_for_narrative_includes_closed_gap_guidance() -> None:
    pack = extract_mobilisation_evidence_pack(_chen_stage1_source_texts(), [ENGAGEMENT_REF, FEE_REF])
    summary = pack_summary_for_narrative(pack)

    assert "do NOT recommend budget confirmation" in summary
    assert "do NOT recommend brief sign-off" in summary
    assert "Geotechnical report" in summary


def test_format_register_rows_table_renders_markdown_table() -> None:
    table = format_register_rows_table(_valid_harrison_clarke_narrative().register_rows)

    assert "| ID | Description | Owner | Status | Due date | Source | Next action |" in table
    assert "| R-001 | Master programme | Architect-PM | Open | 2026-06-28 |" in table


def test_format_internal_audit_narrative_includes_judgements_and_register_table() -> None:
    fragment = format_internal_audit_narrative(_valid_harrison_clarke_narrative())

    assert "- **Judgements**" in fragment
    assert "- **Recommendations**" in fragment
    assert "- **Register rows**" in fragment
    assert "September 2026" in fragment
    assert "Linden" in fragment
    assert "Geotechnical report not on file." in fragment


def test_run_pmp_narrative_model_validates_agent_output() -> None:
    narrative = _valid_harrison_clarke_narrative()
    agent_result = AsyncMock()
    agent_result.output = narrative

    with patch(
        "app.workflows.pmp_narrative.run_agent_with_retry",
        new=AsyncMock(return_value=agent_result),
    ) as run_agent:
        output = run_async(
            run_pmp_narrative_model(
                project=_project(),
                pack=_pack(),
                run_date=RUN_DATE,
            )
        )

    assert output.judgements == narrative.judgements
    run_agent.assert_awaited_once()


def test_run_pmp_narrative_model_completes_required_master_programme_items() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "recommendations": [
                "Owner to confirm working budget ceiling by 2026-06-28.",
                "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
                "Architect-PM to coordinate geotechnical procurement by 2026-06-28.",
            ],
            "register_rows": [
                *_valid_harrison_clarke_narrative().register_rows[1:],
            ],
        }
    )
    agent_result = AsyncMock()
    agent_result.output = narrative

    with patch(
        "app.workflows.pmp_narrative.run_agent_with_retry",
        new=AsyncMock(return_value=agent_result),
    ):
        output = run_async(
            run_pmp_narrative_model(
                project=_project(),
                pack=_pack(),
                run_date=RUN_DATE,
            )
        )

    combined_recommendations = "\n".join(output.recommendations).lower()
    combined_register = "\n".join(
        f"{row.description} {row.next_action}" for row in output.register_rows
    ).lower()

    assert "master programme" in combined_recommendations
    assert "master programme" in combined_register
    validate_pmp_narrative_output(output, _pack(), run_date=RUN_DATE)


def test_run_pmp_narrative_model_repairs_source_and_certifier_scope() -> None:
    narrative = _valid_harrison_clarke_narrative().model_copy(
        update={
            "recommendations": [
                "Owner to appoint a principal certifier by 2026-06-28 to ensure compliance and timely processing of DA submissions.",
                "Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.",
                "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
            ],
            "register_rows": [
                _valid_harrison_clarke_narrative().register_rows[0],
                RegisterRow(
                    id="R-002",
                    description="Linden conflict declaration",
                    owner="Architect-PM",
                    status="Open",
                    due_date="2026-06-28",
                    source="conflict disclosure",
                    next_action="Declare evaluation involvement before tender list lock",
                ),
                _valid_harrison_clarke_narrative().register_rows[2],
            ],
        }
    )
    agent_result = AsyncMock()
    agent_result.output = narrative

    with patch(
        "app.workflows.pmp_narrative.run_agent_with_retry",
        new=AsyncMock(return_value=agent_result),
    ):
        output = run_async(
            run_pmp_narrative_model(
                project=_project(),
                pack=_pack(),
                run_date=RUN_DATE,
            )
        )

    recommendations = "\n".join(output.recommendations).lower()
    conflict_rows = [
        row
        for row in output.register_rows
        if "linden" in f"{row.description} {row.next_action}".lower()
    ]

    assert "da submissions" not in recommendations
    assert "construction certificate pathway" in recommendations
    assert conflict_rows
    assert all(row.source == "fee proposal" for row in conflict_rows)
    validate_pmp_narrative_output(output, _pack(), run_date=RUN_DATE)
