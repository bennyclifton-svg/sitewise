import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.database.project import Project
from app.sitewise.mobilisation_evidence import extract_mobilisation_evidence_pack
from app.sitewise.pmp_assembler import assemble_pmp_markdown
from app.sitewise.pmp_evidence_validation import evidence_grounded_violations
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.workflows.pmp_narrative import (
    PmpNarrativeOutput,
    RegisterRow,
    RiskRow,
)

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


def _narrative() -> PmpNarrativeOutput:
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


def test_assemble_pmp_markdown_merges_narrative_into_scaffold() -> None:
    scaffold = render_pmp_scaffold(_project(), _pack(), "evidence_grounded")
    markdown = assemble_pmp_markdown(
        scaffold,
        _narrative(),
        provenance={"compiler": "hybrid"},
    )

    assert "Pending narrative generation" not in markdown
    assert "- **Judgements**" in markdown
    assert "| R-001 | Master programme |" in markdown
    assert "Owner to confirm working budget ceiling by 2026-06-28." in markdown
    assert "Geotechnical report not on file." in markdown
    assert "| Planning pathway / DA programme slip | Owner |" in markdown


def test_assemble_pmp_markdown_emits_single_registers_footer() -> None:
    scaffold = render_pmp_scaffold(_project(), _pack(), "evidence_grounded")
    markdown = assemble_pmp_markdown(scaffold, _narrative(), provenance={"compiler": "hybrid"})
    footer = (
        "Registers to open: action, decision, risk, authority approvals, consultant appointment."
    )

    assert markdown.count(footer) == 1


def test_assemble_pmp_markdown_passes_evidence_and_structure_validation() -> None:
    scaffold = render_pmp_scaffold(_project(), _pack(), "evidence_grounded")
    markdown = assemble_pmp_markdown(scaffold, _narrative(), provenance={"compiler": "hybrid"})
    source_texts = [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]

    assert (
        evidence_grounded_violations(
            markdown,
            [ENGAGEMENT_REF, FEE_REF],
            source_texts=source_texts,
        )
        == []
    )
    assert (
        greenfield_structure_violations(
            markdown,
            archetype="new-dwelling",
            user_role="architect-pm",
        )
        == []
    )
