import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from openai import OpenAIError
from pydantic_ai.exceptions import ModelHTTPError

from app.database.project import Project
from app.retrieval.schemas import SourcePassage
from app.sitewise.pmp_sources import required_platform_paths, required_section_headings
from app.workflows.create_pmp import (
    PmpDraftOutput,
    canonical_pmp_workspace_path,
    draft_workspace_path,
    RUNTIME_HYBRID_NAME,
    _source_excerpt_chars,
    normalize_pmp_markdown,
    retrieve_create_pmp_sources,
    run_create_pmp_workflow,
    validate_pmp_output,
    CREATE_PMP_EVIDENCE_DOC_CHARS,
    CREATE_PMP_CHUNK_EXCERPT_CHARS,
)
from app.workflows.pmp_narrative import PmpNarrativeOutput, RegisterRow
from tests.conftest import run_async

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "chen-residence"

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _project(**overrides) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "greenfield-demo",
        "title": "Greenfield Demo",
        "workspace_path": "04-projects/greenfield-demo",
        "phase": "brief-planning",
        "archetype": "renovation",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": None,
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def test_draft_workspace_path_uses_stable_pmp_md() -> None:
    assert (
        draft_workspace_path(_project(), version=3)
        == "04-projects/greenfield-demo/00-brief-pmp/PMP.md"
    )


def test_canonical_pmp_workspace_path_normalises_legacy_draft_paths() -> None:
    assert (
        canonical_pmp_workspace_path(
            "04-projects/demo/00-brief-pmp/PMP-draft-v01.md"
        )
        == "04-projects/demo/00-brief-pmp/PMP.md"
    )


def _valid_pmp_markdown(user_role: str = "architect-pm") -> str:
    sections = required_section_headings(user_role)
    greenfield_terms = (
        "Latent conditions and dilapidation due diligence. "
        "Stage 1 concept design. Contingency 5-10%. "
        "What this means for you — what we need from you. "
        "Slab frame lockup fixing programme milestones. "
        "2-3 invited builders for head-builder procurement. "
        "Recommendation: owner to confirm planning pathway by 2026-06-21."
    )
    body = "\n\n".join(
        f"## {heading}\n\nAssumption content for {heading}. {greenfield_terms}"
        for heading in sections
    )
    return f"# Project Management Plan\n\n{body}"


def _valid_evidence_grounded_pmp_markdown(user_role: str = "architect-pm") -> str:
    markdown = _valid_pmp_markdown(user_role)
    evidence_basis = """## Evidence basis and document control

Status: draft, review-only, not issued. Version v01.
Evidence on file: Harrison Clarke Studio engagement letter (executed 16/05/2026);
fee proposal (28/04/2026).
Gaps: formal owner project brief sign-off, geotech, certifier appointment, construction budget.

| Section | Evidence status | Ref |
| --- | --- | --- |
| Appointment & fee | Grounded | engagement letter |
| Project understanding | Partial | fee proposal |
| Construction budget | Not evidenced | — |
"""
    internal_audit = """## Internal audit layer

- **Facts**
- HCS engaged as architect-PM; engagement executed 16/05/2026.
- Fixed fee $148,500 ex GST on staged triggers per engagement letter.
- DA pathway assumed (not CDC) per fee proposal.
- **Assumptions**
- Construction budget not evidenced.
- Certifier not yet appointed.
- **Judgements**
- Post-engagement mobilisation posture; master programme required before September 2026 DA target.
- **Recommendations**
- Owner to confirm working budget ceiling by 2026-06-28.
- Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.
- Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.
- **Workflow warnings**
- Geotech and certifier not yet on file.
"""
    markdown = _replace_pmp_section(markdown, "Evidence basis and document control", evidence_basis)
    project_overview = """## Project overview

Archetype: new dwelling. Role: Architect-PM. State: NSW.
Owners: Michael and Sarah Chen.
Site: 14 Wattle Grove, Lindfield NSW 2070.
Dwelling: knockdown-rebuild Class 1a (~285 m² GFA per fee proposal).
Mobilisation: post-engagement (HCS engagement executed 16/05/2026).
Assumption: working construction budget not yet evidenced.
"""
    markdown = _replace_pmp_section(markdown, "Project overview", project_overview)
    markdown = _replace_pmp_section(markdown, "Internal audit layer", internal_audit)
    return markdown


def _replace_pmp_section(markdown: str, heading: str, replacement: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            output.extend(replacement.rstrip().splitlines())
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("## "):
                index += 1
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


def _valid_seed_consulted() -> list[str]:
    return [
        "seed/renovation-guide.md",
        "seed/role-architect-pm.md",
        "seed/setup-and-commission-guide.md",
        "seed/contract-administration-guide.md",
        "seed/cost-management-principles.md",
        "seed/program-scheduling-guide.md",
        "seed/procurement-quoting-guide.md",
    ]


def _passage(
    *,
    project: str,
    source_type: str,
    relative_path: str,
    whole_document: bool = False,
) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content="The project brief requires a project management plan.",
        project=project,
        phase="reference",
        source_type=source_type,
        document_class="reference_guide" if source_type == "reference" else source_type,
        filename=relative_path.split("/")[-1],
        relative_path=relative_path,
        document_metadata=(
            {"knowledge_scope": "platform"}
            if whole_document and source_type in ("doctrine", "reference")
            else None
        ),
        chunk_metadata={"whole_document": True} if whole_document else None,
        score=1.0,
    )


def _project_source_texts() -> list[str]:
    return [
        "Dear Michael and Sarah Chen,\n"
        "Re: Chen Residence, 14 Wattle Grove, Lindfield NSW 2070"
    ]


def test_create_pmp_blocks_when_overlay_gate_fails() -> None:
    result = run_async(
        run_create_pmp_workflow(
            AsyncMock(),
            user_id=USER_ID,
            project=_project(archetype="TBC"),
            thread_id=None,
        )
    )

    assert result.status == "blocked"
    assert result.gate.ready is False
    assert result.draft is None


def test_create_pmp_fails_when_platform_and_project_sources_missing() -> None:
    with (
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([], [])),
        ),
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "failed"
    assert "doctrine and seed" in (result.message or "")


def test_create_pmp_greenfield_from_platform_whole_documents() -> None:
    output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=_valid_pmp_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md", "reference:seed/setup-and-commission-guide.md"],
    )
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_pmp"
    draft.version = 1
    draft.status = "draft"
    draft.title = output.title
    draft.workspace_path = "04-projects/greenfield-demo/00-brief-pmp/PMP.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = output.markdown
    draft.model = "gpt-4o-mini"
    draft.runtime = "clerk-sitewise-create-pmp"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 7, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 7, tzinfo=timezone.utc)

    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/setup-and-commission-guide.md",
        whole_document=True,
    )

    with (
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_pmp.run_create_pmp_model",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "complete"
    assert result.draft is not None
    create_draft.assert_awaited_once()
    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["draft_mode"] == "platform_seeded"
    retrieval_trace = next(event for event in result.trace if event.step == "retrieval")
    assert retrieval_trace.metadata["platform_retrieval"] == "overlay_mandatory_paths"
    assert retrieval_trace.metadata["draft_mode"] == "platform_seeded"


def test_create_pmp_saves_evidence_grounded_draft() -> None:
    output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=_valid_evidence_grounded_pmp_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[
            "project_evidence:greenfield-demo/02-consultant/architect/"
            "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
            "project_evidence:greenfield-demo/02-consultant/architect/"
            "02-fee-proposal-harrison-clarke-studio.md#chunk=def",
        ],
        context_refs=["reference:seed/new-dwelling-guide.md"],
    )
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_pmp"
    draft.version = 1
    draft.status = "draft"
    draft.title = output.title
    draft.workspace_path = "04-projects/greenfield-demo/00-brief-pmp/PMP.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = output.markdown
    draft.model = "gpt-4o-mini"
    draft.runtime = "clerk-sitewise-create-pmp"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 7, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 7, tzinfo=timezone.utc)

    with (
        patch("app.workflows.create_pmp.settings.pmp_hybrid_compiler", False),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(
                return_value=[
                    _passage(
                        project="greenfield-demo",
                        source_type="project_evidence",
                        relative_path="greenfield-demo/brief.md",
                        whole_document=True,
                    )
                ]
            ),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(
                return_value=(
                    [
                        _passage(
                            project="seed",
                            source_type="reference",
                            relative_path="seed/new-dwelling-guide.md",
                            whole_document=True,
                        )
                    ],
                    [],
                )
            ),
        ),
        patch(
            "app.workflows.create_pmp.run_create_pmp_model",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "complete"
    assert result.draft is not None
    create_draft.assert_awaited_once()
    assert create_draft.await_args.kwargs["provenance_metadata"]["draft_mode"] == "evidence_grounded"


def test_validate_pmp_output_allows_empty_evidence_refs_for_platform_seeded() -> None:
    output = PmpDraftOutput(
        title="PMP",
        markdown=_valid_pmp_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_pmp_output(
        output,
        "platform_seeded",
        archetype="renovation",
        user_role="architect-pm",
    )


def test_normalize_pmp_markdown_strips_bullet_prefixed_table_rows() -> None:
    raw = "## Section\n\n- | Col | Val |\n  | --- | --- |\n  | A | 1 |\n"
    normalized = normalize_pmp_markdown(raw)
    assert "- | Col |" not in normalized
    assert "| Col | Val |" in normalized


def _valid_builder_pmp_markdown() -> str:
    sections = required_section_headings("builder")
    greenfield_terms = (
        "Latent conditions contingency 5-10%. HBCF per-project certificate. "
        "HIA Schedule of Variations variation register. EOT notice within contract window. "
        "Recommendation: owner to sign head contract within 2 weeks."
    )
    procurement = (
        "## Procurement and subcontractor posture\n\n"
        "| Trade | Appointed | Licence verified | Insurance | Scope stage | Status |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Demolition | TBC | Assumption | Assumption | Pre-start | Assumption |\n"
        "| Plumbing | TBC | Assumption | Assumption | Construction | Assumption |\n"
        "| Electrical | TBC | Assumption | Assumption | Construction | Assumption |\n"
        "| Waterproofing | TBC | Assumption | Assumption | Construction | Assumption |\n"
        f"{greenfield_terms}\n"
    )
    risks = (
        "## Risks, decisions and next actions\n\n"
        "| Risk | Owner | Status | Next action | Due |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Latent conditions | Builder | Assumption | Stage investigation | 2026-07-01 |\n"
        "| Tie-ins | Builder | Assumption | Detail junction spec | 2026-07-01 |\n"
        "| Waterproofing | Builder | Assumption | Engage specialist | 2026-07-01 |\n"
        "| Live occupancy | Owner | Assumption | Agree staging plan | 2026-07-01 |\n"
        "| Approval pathway | Builder | Assumption | Test CDC vs DA | 2026-07-01 |\n"
    )
    audit = (
        "## Internal audit layer\n\n"
        "- **Facts**\n- Draft mobilisation plan only.\n"
        "- **Assumptions**\n- No contract filed.\n"
        "- **Judgements**\n- Pre-contract mobilisation posture.\n"
        "- **Recommendations**\n- Obtain HBCF by 2026-07-01.\n"
    )
    body_parts = []
    for heading in sections:
        if heading == "Procurement and subcontractor posture":
            body_parts.append(procurement.strip())
        elif heading == "Risks, decisions and next actions":
            body_parts.append(risks.strip())
        elif heading == "Internal audit layer":
            body_parts.append(audit.strip())
        else:
            body_parts.append(
                f"## {heading}\n\nAssumption content. {greenfield_terms}"
            )
    return "\n\n".join(body_parts)


def test_validate_pmp_output_accepts_structured_builder_greenfield() -> None:
    output = PmpDraftOutput(
        title="Builder Mobilisation Plan",
        markdown=_valid_builder_pmp_markdown(),
        seed_consulted=[
            "seed/renovation-guide.md",
            "seed/role-builder.md",
            "seed/setup-and-commission-guide.md",
            "seed/contract-administration-guide.md",
            "seed/cost-management-principles.md",
            "seed/program-scheduling-guide.md",
            "seed/procurement-quoting-guide.md",
        ],
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_pmp_output(
        output,
        "platform_seeded",
        archetype="renovation",
        user_role="builder",
    )


def test_validate_pmp_output_fails_builder_with_invited_builders_antipattern() -> None:
    markdown = _valid_builder_pmp_markdown().replace(
        "Pre-start",
        "2-3 invited builders",
        1,
    )
    output = PmpDraftOutput(
        title="Builder Mobilisation Plan",
        markdown=markdown,
        seed_consulted=[
            "seed/renovation-guide.md",
            "seed/role-builder.md",
            "seed/setup-and-commission-guide.md",
            "seed/contract-administration-guide.md",
            "seed/cost-management-principles.md",
            "seed/program-scheduling-guide.md",
            "seed/procurement-quoting-guide.md",
        ],
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    try:
        validate_pmp_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="builder",
        )
    except Exception as exc:
        assert "structural issues" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for builder antipattern")


def test_validate_pmp_output_fails_when_greenfield_markers_missing() -> None:
    thin_markdown = "\n\n".join(
        f"## {heading}\n\nShort generic paragraph."
        for heading in required_section_headings("architect-pm")
    )
    output = PmpDraftOutput(
        title="PMP",
        markdown=f"# Project Management Plan\n\n{thin_markdown}",
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    try:
        validate_pmp_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="architect-pm",
        )
    except Exception as exc:
        assert "depth markers" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for missing greenfield markers")


def test_validate_pmp_output_fails_when_mandatory_seed_missing() -> None:
    output = PmpDraftOutput(
        title="PMP",
        markdown=_valid_pmp_markdown(),
        seed_consulted=["seed/role-architect-pm.md"],
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    try:
        validate_pmp_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="architect-pm",
        )
    except Exception as exc:
        assert "mandatory seeds" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for missing seeds")


def test_validate_pmp_output_fails_evidence_grounded_contradictions() -> None:
    output = PmpDraftOutput(
        title="PMP",
        markdown=_valid_pmp_markdown().replace(
            "## Evidence basis and document control",
            "## Evidence basis and document control\n\n"
            "Source hierarchy: project evidence (none yet).",
        ),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[
            "project_evidence:greenfield-demo/02-consultant/architect/"
            "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
        ],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    try:
        validate_pmp_output(
            output,
            "evidence_grounded",
            archetype="renovation",
            user_role="architect-pm",
        )
    except Exception as exc:
        assert "evidence_grounded fidelity" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for evidence contradictions")


def test_validate_pmp_output_accepts_evidence_grounded_faithful_draft() -> None:
    output = PmpDraftOutput(
        title="PMP",
        markdown=_valid_evidence_grounded_pmp_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[
            "project_evidence:greenfield-demo/02-consultant/architect/"
            "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
            "project_evidence:greenfield-demo/02-consultant/architect/"
            "02-fee-proposal-harrison-clarke-studio.md#chunk=def",
        ],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_pmp_output(
        output,
        "evidence_grounded",
        archetype="renovation",
        user_role="architect-pm",
        source_texts=_project_source_texts(),
    )


def test_source_excerpt_chars_uses_full_text_for_whole_project_documents() -> None:
    passage = _passage(
        project="greenfield-demo",
        source_type="project_evidence",
        relative_path="greenfield-demo/brief.md",
        whole_document=True,
    )
    assert _source_excerpt_chars(passage) == CREATE_PMP_EVIDENCE_DOC_CHARS

    chunk_passage = _passage(
        project="greenfield-demo",
        source_type="project_evidence",
        relative_path="greenfield-demo/brief.md",
    )
    assert _source_excerpt_chars(chunk_passage) == CREATE_PMP_CHUNK_EXCERPT_CHARS


def test_expand_project_passages_to_whole_documents() -> None:
    from app.database.source_document import SourceDocument
    from app.workflows.create_pmp import expand_project_passages_to_whole_documents

    doc_id = uuid.uuid4()
    chunk_passage = _passage(
        project="greenfield-demo",
        source_type="project_evidence",
        relative_path="04-projects/greenfield-demo/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md",
    )
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/setup-and-commission-guide.md",
        whole_document=True,
    )
    source_doc = SourceDocument(
        id=doc_id,
        project="greenfield-demo",
        phase="reference",
        document_class="project_evidence",
        filename="01-engagement-letter-harrison-clarke-studio.md",
        relative_path=chunk_passage.relative_path,
        normalized_content="Full engagement letter body with owner names and site address.",
        source_type="project_evidence",
    )
    session = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = [source_doc]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=execute_result)

    expanded = run_async(
        expand_project_passages_to_whole_documents(
            session,
            project=_project(),
            passages=[chunk_passage, platform_passage],
        )
    )

    assert len(expanded) == 2
    project_passages = [p for p in expanded if p.project == "greenfield-demo"]
    assert len(project_passages) == 1
    assert project_passages[0].content.startswith("Full engagement letter")
    assert project_passages[0].chunk_metadata.get("whole_document") is True


def test_create_pmp_fails_when_mandatory_platform_paths_missing() -> None:
    with (
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([], ["seed/renovation-guide.md"])),
        ),
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "failed"
    assert "mandatory platform sources" in (result.message or "")


def test_create_pmp_returns_failed_response_when_project_retrieval_openai_fails() -> None:
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/setup-and-commission-guide.md",
        whole_document=True,
    )

    with (
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(side_effect=OpenAIError("embedding request failed")),
        ),
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "failed"
    assert "OpenAI request failed" in (result.message or "")
    assert result.trace[-1].step == "retrieval"
    assert result.trace[-1].status == "failed"
    assert result.trace[-1].metadata["error_type"] == "OpenAIError"


def test_create_pmp_returns_failed_response_when_model_request_fails() -> None:
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/setup-and-commission-guide.md",
        whole_document=True,
    )

    with (
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_pmp.run_create_pmp_model",
            new=AsyncMock(
                side_effect=ModelHTTPError(
                    status_code=401,
                    model_name="openai-chat:gpt-4o-mini",
                    body={"error": {"message": "invalid api key"}},
                )
            ),
        ),
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "failed"
    assert "OpenAI authentication failed" in (result.message or "")
    assert result.trace[-1].step == "model"
    assert result.trace[-1].status == "failed"
    assert result.trace[-1].metadata["error_type"] == "ModelHTTPError"
    assert result.trace[-1].metadata["status_code"] == 401


def test_retrieve_create_pmp_sources_uses_mandatory_platform_paths() -> None:
    session = AsyncMock()
    project_passage = _passage(
        project="greenfield-demo",
        source_type="project_evidence",
        relative_path="greenfield-demo/brief.md",
        whole_document=True,
    )
    platform_passage = _passage(
        project="seed",
        source_type="doctrine",
        relative_path="docs/clerk-brief.md",
        whole_document=True,
    )

    with (
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=[project_passage]),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ) as load_platform,
    ):
        passages, project_count, platform_count, draft_mode, missing = run_async(
            retrieve_create_pmp_sources(session, project=_project())
        )

    assert project_count == 1
    assert platform_count == 1
    assert draft_mode == "evidence_grounded"
    assert missing == []
    assert len(passages) == 2
    load_platform.assert_awaited_once()


def _evidence_passage(relative_path: str, content: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=content,
        project="greenfield-demo",
        phase="reference",
        source_type="project_evidence",
        document_class="project_evidence",
        filename=relative_path.split("/")[-1],
        relative_path=relative_path,
        document_metadata=None,
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


def _platform_passages_for_project(project: Project) -> list[SourcePassage]:
    paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=project.user_role or "",
    )
    passages: list[SourcePassage] = []
    for path in paths:
        source_type = "doctrine" if path.startswith("docs/") else "reference"
        passages.append(
            _passage(
                project="seed",
                source_type=source_type,
                relative_path=path,
                whole_document=True,
            )
        )
    return passages


def _harrison_clarke_narrative() -> PmpNarrativeOutput:
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
        ],
        risk_rows=[],
        workflow_warnings=[
            "Geotechnical report not on file.",
            "Certifier not yet appointed.",
        ],
    )


def test_create_pmp_hybrid_compiler_saves_assembled_draft() -> None:
    project = _project(archetype="new-dwelling", user_role="architect-pm", state="NSW")
    engagement_path = (
        "greenfield-demo/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md"
    )
    fee_path = (
        "greenfield-demo/02-consultant/architect/"
        "02-fee-proposal-harrison-clarke-studio.md"
    )
    mobilisation_passages = [
        _evidence_passage(
            engagement_path,
            (FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md").read_text(
                encoding="utf-8"
            ),
        ),
        _evidence_passage(
            fee_path,
            (FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md").read_text(
                encoding="utf-8"
            ),
        ),
    ]
    platform_passages = _platform_passages_for_project(project)
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_pmp"
    draft.version = 1
    draft.status = "draft"
    draft.title = "Project Management Plan"
    draft.workspace_path = "04-projects/greenfield-demo/00-brief-pmp/PMP.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = "# Project Management Plan"
    draft.model = "gpt-4o-mini"
    draft.runtime = RUNTIME_HYBRID_NAME
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 8, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 8, tzinfo=timezone.utc)

    with (
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=mobilisation_passages),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.workflows.pmp_narrative.run_pmp_narrative_model",
            new=AsyncMock(return_value=_harrison_clarke_narrative()),
        ),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
            )
        )

    assert result.status == "complete"
    assert result.draft is not None
    create_draft.assert_awaited_once()
    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "hybrid"
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_HYBRID_NAME
    markdown = create_draft.await_args.kwargs["content_markdown"]
    assert "September 2026" in markdown
    assert "| R-001 | Master programme |" in markdown
    assert "Pending narrative generation" not in markdown
    steps = {event.step for event in result.trace}
    assert {"extract", "scaffold", "narrative", "assemble"}.issubset(steps)
