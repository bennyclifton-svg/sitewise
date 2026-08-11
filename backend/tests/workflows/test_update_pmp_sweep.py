import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.sitewise.gate import overlay_status

import pytest

from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.selective_refresh import apply_document_refresh
from app.projects.artefact_context import build_pmp_context
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ProjectGenerationContext
from app.retrieval.generation import RetrievalBudget
from app.schemas.projects import WorkflowTraceEvent
from app.sitewise.mobilisation_evidence import (
    MobilisationEvidencePack,
    merge_evidence_packs,
)
from app.sitewise.pmp_corpus import (
    CorpusListingResult,
    is_active_pmp_corpus_document,
    list_current_pmp_corpus_documents,
)
from app.sitewise.pmp_evidence_validation import apply_corpus_evidence_downgrades
from app.sitewise.pmp_sweep import (
    compute_evidence_changed,
    compute_sections_changed,
    evidence_ref_path,
    sweep_current_pmp_corpus,
)
from app.workflows.create_pmp import (
    CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS,
    PmpDraftOutput,
)
from app.workflows.update_pmp import run_update_pmp_workflow
from tests.conftest import run_async
from tests.workflows.test_create_pmp import (
    _valid_evidence_grounded_pmp_markdown,
    _valid_seed_consulted,
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
BASELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture(autouse=True)
def _no_consultant_fact_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests pass bare AsyncMock sessions that don't model chained
    # session.execute(...).scalars().all() calls; skip the reconcile side
    # effect so those mocks don't have to.
    monkeypatch.setattr(
        "app.workflows.update_pmp._reconcile_consultant_facts_for_pmp",
        AsyncMock(return_value=0),
    )


def _document(
    *,
    relative_path: str,
    filename: str | None = None,
    metadata: dict | None = None,
    content: str = "Letter of engagement content.",
    updated_at: datetime | None = None,
) -> SourceDocument:
    return SourceDocument(
        id=uuid.uuid4(),
        project="demo-project",
        phase="brief-planning",
        document_type="brief",
        document_class="brief",
        ingest_mode="whole",
        document_metadata=metadata,
        content_hash="abc123",
        source_type="project_evidence",
        filename=filename or relative_path.rsplit("/", 1)[-1],
        relative_path=relative_path,
        normalized_content=content,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=updated_at or datetime(2026, 6, 2, tzinfo=timezone.utc),
    )


def _taxonomy_project(**overrides) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "taxonomy-project",
        "title": "Residential House",
        "workspace_path": "04-projects/taxonomy-project",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": "residential",
        "work_type": "new",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": {
            "taxonomy": {
                "subclasses": ["house"],
                "scale": {"gfa_sqm": 260},
                "budget": "$1,000,000",
            }
        },
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def _baseline_draft() -> DraftArtifact:
    return DraftArtifact(
        id=BASELINE_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=1,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/taxonomy-project/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=_valid_evidence_grounded_pmp_markdown(),
        model="gpt-5.6-terra",
        runtime="clerk-sitewise-create-pmp-adaptive-scaffold",
        provenance_metadata={
            "evidence_refs": [
                "project_evidence:04-projects/taxonomy-project/01-engagement-letter.md#chunk=1"
            ]
        },
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def _generation_context() -> ProjectGenerationContext:
    return ProjectGenerationContext(
        project_id=PROJECT_ID,
        context_version=9,
        identity={},
        taxonomy={},
        scale={},
        complexity={},
        scope={},
        commercial={},
        programme={},
        approvals={},
        stakeholders={},
        derived_risks=[],
    )


def test_is_active_pmp_corpus_document_excludes_superseded_unless_retained() -> None:
    active = _document(
        relative_path="04-projects/demo/current.md",
        metadata={"status": "current"},
    )
    superseded = _document(
        relative_path="04-projects/demo/old.md",
        metadata={"status": "superseded"},
    )
    retained = _document(
        relative_path="04-projects/demo/retained.md",
        metadata={"status": "superseded", "retained_active": True},
    )
    assert is_active_pmp_corpus_document(active) is True
    assert is_active_pmp_corpus_document(superseded) is False
    assert is_active_pmp_corpus_document(retained) is True


def test_compute_sections_changed_detects_heading_body_diff() -> None:
    baseline = "## Scope\n\nAlpha\n\n## Risks\n\nOne\n"
    output = "## Scope\n\nBeta\n\n## Risks\n\nOne\n"
    assert compute_sections_changed(baseline, output) == ["Scope"]


def test_compute_evidence_changed_tracks_added_and_removed_paths() -> None:
    changed = compute_evidence_changed(
        previous_refs=["project_evidence:old.md#chunk=1"],
        current_refs=["project_evidence:new.md#chunk=2"],
    )
    assert changed["added"] == ["new.md"]
    assert changed["removed"] == ["old.md"]
    assert changed["superseded"] == ["old.md"]


def test_apply_corpus_evidence_downgrades_grounded_rows() -> None:
    markdown = (
        "## Evidence basis and document control\n\n"
        "| Section | Evidence status | Ref |\n"
        "| --- | --- | --- |\n"
        "| Appointment & fee | Grounded | engagement letter |\n"
        "| Budget | User provided | owner brief |\n"
    )
    updated, meta = apply_corpus_evidence_downgrades(
        markdown,
        removed_paths={"04-projects/demo/01-engagement-letter.md"},
        current_source_texts=[],
    )
    assert "Not evidenced" in updated
    assert "current corpus no longer supports" in updated
    assert meta["downgraded"]
    assert meta["conflicted"]


def test_evidence_ref_path_normalises_chunk_suffix() -> None:
    assert evidence_ref_path("project_evidence:04-projects/demo/a.md#chunk=123") == (
        "04-projects/demo/a.md"
    )


class _FakeSession:
    def __init__(self, documents: list[SourceDocument]):
        self._documents = documents

    async def execute(self, _stmt):
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: self._documents)
        )


@pytest.mark.anyio
async def test_list_current_pmp_corpus_documents_filters_and_caps() -> None:
    docs = [
        _document(relative_path=f"04-projects/demo/doc-{index}.md")
        for index in range(3)
    ] + [
        _document(
            relative_path="04-projects/demo/superseded.md",
            metadata={"status": "superseded"},
        )
    ]
    session = _FakeSession(docs)
    result = await list_current_pmp_corpus_documents(
        session,
        project_id=PROJECT_ID,
        max_documents=2,
    )
    assert isinstance(result, CorpusListingResult)
    assert len(result.documents) == 2
    assert result.skipped_superseded == 1
    assert result.capped is True


@pytest.mark.anyio
async def test_revision_dedupe_keeps_distinct_drawings_with_generic_document_number() -> (
    None
):
    section_2 = _document(
        relative_path="04-projects/demo/03-design/Section 2 Rev DWN.pdf",
        metadata={
            "document_number": "Section",
            "title": "2",
            "revision": "DWN",
        },
        updated_at=datetime(2026, 7, 24, 11, 44, tzinfo=timezone.utc),
    )
    section_3 = _document(
        relative_path="04-projects/demo/03-design/Section 3 Rev DWN.pdf",
        metadata={
            "document_number": "Section",
            "title": "3",
            "revision": "DWN",
        },
        updated_at=datetime(2026, 7, 24, 11, 45, tzinfo=timezone.utc),
    )

    result = await list_current_pmp_corpus_documents(
        _FakeSession([section_2, section_3]),
        project_id=PROJECT_ID,
    )

    assert {document.filename for document in result.documents} == {
        "Section 2 Rev DWN.pdf",
        "Section 3 Rev DWN.pdf",
    }
    assert result.skipped_revision_duplicate == 0


@pytest.mark.anyio
async def test_revision_dedupe_keeps_distinct_annexures_with_generic_number() -> None:
    ppr = _document(
        relative_path="04-projects/demo/_inbox/ANX Q PPR [E].pdf",
        metadata={
            "document_number": "ANX",
            "title": "Q PPR",
            "revision": "E",
        },
        updated_at=datetime(2026, 7, 20, 10, 3, tzinfo=timezone.utc),
    )
    da_matrix = _document(
        relative_path="04-projects/demo/_inbox/ANX U DA MATRIX [A].pdf",
        metadata={
            "document_number": "ANX",
            "title": "U DA MATRIX",
            "revision": "A",
        },
        updated_at=datetime(2026, 7, 20, 20, 13, tzinfo=timezone.utc),
    )

    result = await list_current_pmp_corpus_documents(
        _FakeSession([ppr, da_matrix]),
        project_id=PROJECT_ID,
    )

    assert {document.filename for document in result.documents} == {
        "ANX Q PPR [E].pdf",
        "ANX U DA MATRIX [A].pdf",
    }
    assert result.skipped_revision_duplicate == 0


@pytest.mark.anyio
async def test_revision_dedupe_keeps_latest_real_document_number_despite_title_variation() -> (
    None
):
    old = _document(
        relative_path="04-projects/demo/03-design/A-101 Rev A.pdf",
        metadata={
            "document_number": "A-101",
            "title": "Ground floor plan",
            "revision": "A",
        },
        updated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )
    current = _document(
        relative_path="04-projects/demo/03-design/A-101 Rev B.pdf",
        metadata={
            "document_number": "A-101",
            "title": "Proposed ground floor",
            "revision": "B",
        },
        updated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    result = await list_current_pmp_corpus_documents(
        _FakeSession([old, current]),
        project_id=PROJECT_ID,
    )

    assert [document.filename for document in result.documents] == ["A-101 Rev B.pdf"]
    assert result.skipped_revision_duplicate == 1


@pytest.mark.anyio
async def test_sweep_current_pmp_corpus_batches_and_emits_trace() -> None:
    engagement = _document(
        relative_path="04-projects/demo/02-consultant/architect/01-engagement-letter.md",
        content=(
            "Letter of engagement\n\n"
            "## Appointment\n\n"
            "appointed as **architect and project manager**\n\n"
            "## Fee basis\n\n"
            "| Stage | Trigger | Fee |\n"
            "| --- | --- | --- |\n"
            "| Mobilisation | Signed | $1,000 |\n"
        ),
    )
    session = _FakeSession([engagement])
    project = SimpleNamespace(id=PROJECT_ID, slug="demo-project")
    result = await sweep_current_pmp_corpus(
        session,
        project=project,
        previous_evidence_refs=[],
    )
    assert len(result.passages) == 1
    assert result.trace_events
    assert result.trace_events[0].step == "evidence_sweep"
    assert result.evidence_changed["added"]


def test_merge_evidence_packs_scales_to_many_batches() -> None:
    merged = MobilisationEvidencePack()
    for index in range(100):
        merged = merge_evidence_packs(
            merged,
            MobilisationEvidencePack(
                other_evidence=[f"Document {index} on file"],
                evidence_refs=[f"project_evidence:doc-{index}.md#chunk={index}"],
            ),
        )
    assert len(merged.other_evidence) == 100
    assert len(merged.evidence_refs) == 100


def test_batch_count_for_100_documents() -> None:
    assert (100 + CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS - 1) // (
        CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS
    ) == 13


def test_update_pmp_taxonomy_uses_corpus_sweep_not_delta() -> None:
    project = _taxonomy_project(project_context_version=9)
    baseline = _baseline_draft()
    generation_context = _generation_context()
    semantic_search = AsyncMock()

    async def retrieve_sources(_session, *, project, generation_context=None):
        del project
        if generation_context is None or generation_context.critical_unknowns():
            await semantic_search()
        return [], 0, 2, "platform_seeded", []

    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    created_draft = DraftArtifact(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=2,
        status="draft",
        title="Project Management Plan",
        workspace_path=baseline.workspace_path,
        author_user_id=USER_ID,
        content_markdown=baseline.content_markdown,
        model="gpt-5.6-terra",
        runtime="clerk-sitewise-update-pmp",
        provenance_metadata={},
        created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )

    sweep_result = SimpleNamespace(
        passages=(),
        merged_pack=SimpleNamespace(evidence_refs=[]),
        evidence_refs=(),
        listing=SimpleNamespace(
            documents=(),
            total_indexed=0,
            skipped_superseded=0,
            skipped_revision_duplicate=0,
            capped=False,
        ),
        evidence_changed={
            "added": [],
            "removed": ["04-projects/taxonomy-project/01-engagement-letter.md"],
            "superseded": ["04-projects/taxonomy-project/01-engagement-letter.md"],
            "downgraded": [],
            "conflicted": [],
        },
        trace_events=(
            WorkflowTraceEvent(
                step="evidence_sweep",
                status="complete",
                message="Active corpus is empty",
                metadata={"batch_index": 0},
            ),
        ),
    )

    with (
        patch(
            "app.workflows.update_pmp.overlay_status",
            return_value=overlay_status(
                archetype="new-dwelling",
                state="NSW",
            ),
        ),
        patch(
            "app.workflows.update_pmp.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.update_pmp.get_latest_draft_artifact",
            new=AsyncMock(return_value=baseline),
        ),
        patch(
            "app.workflows.update_pmp.retrieve_create_pmp_sources",
            new=AsyncMock(side_effect=retrieve_sources),
        ) as retrieve_sources_mock,
        patch(
            "app.workflows.update_pmp.sweep_current_pmp_corpus",
            new=AsyncMock(return_value=sweep_result),
        ) as sweep_mock,
        patch(
            "app.workflows.create_pmp.retrieve_project_evidence_delta",
            new=AsyncMock(),
        ) as delta_mock,
        patch(
            "app.workflows.update_pmp.run_update_pmp_model",
            new=AsyncMock(
                return_value=PmpDraftOutput(
                    title="Project Management Plan",
                    markdown=baseline.content_markdown,
                    seed_consulted=_valid_seed_consulted()
                    + ["seed/new-dwelling-guide.md", "seed/role-architect-pm.md"],
                    evidence_refs=[],
                    context_refs=["doctrine:docs/clerk-brief.md"],
                )
            ),
        ) as run_model_mock,
        patch(
            "app.workflows.update_pmp.validate_update_pmp_output",
            return_value=None,
        ),
        patch(
            "app.workflows.update_pmp.create_draft_artifact",
            new=AsyncMock(return_value=created_draft),
        ) as create_draft_mock,
        patch("app.workflows.create_pmp.sync_pmp_draft_workspace", new=AsyncMock()),
        patch("app.workflows.update_pmp.sync_decisions_from_markdown", new=AsyncMock()),
        patch("app.workflows.update_pmp._persist_trace_message", new=AsyncMock()),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=2),
        ),
        patch(
            "app.workflows.update_pmp.build_generation_brief",
            wraps=build_generation_brief,
        ) as build_brief_mock,
        patch(
            "app.workflows.update_pmp.apply_document_refresh",
            wraps=apply_document_refresh,
        ) as refresh_mock,
    ):
        response = run_async(
            run_update_pmp_workflow(
                session,
                user_id=USER_ID,
                project=project,
                thread_id=None,
                generation_context=generation_context,
            )
        )

    retrieve_sources_mock.assert_awaited_once_with(
        session,
        project=project,
        generation_context=generation_context,
    )
    semantic_search.assert_not_awaited()
    sweep_mock.assert_awaited_once()
    delta_mock.assert_not_awaited()
    assert response.status == "complete"
    assert (
        create_draft_mock.await_args.kwargs["model"] == "openai-responses:gpt-5.6-terra"
    )
    provenance = create_draft_mock.await_args.kwargs["provenance_metadata"]
    assert provenance["model_label"] == "GPT-5.6 Terra (balanced)"
    assert provenance["model_provider"] == "openai-api"
    assert provenance["model_execution_provider"] == "openai-responses"
    assert provenance["model_execution_id"] == "openai-responses:gpt-5.6-terra"
    assert "sections_changed" in provenance
    assert "evidence_changed" in provenance
    assert provenance["active_corpus_documents"] == 0
    assert "proposed_delete" in provenance["incremental_update"]
    assert provenance["incremental_update"]["input_hash"]
    build_brief_mock.assert_called_once()
    generation_brief = run_model_mock.await_args.kwargs["generation_brief"]
    assert provenance["generation_brief"] == generation_brief.model_dump(mode="json")
    assert (
        provenance["generation_manifest"]["input_fingerprint"]
        == generation_brief.input_fingerprint
    )
    assert provenance["generation_manifest"][
        "generation_brief"
    ] == generation_brief.model_dump(mode="json")
    assert refresh_mock.call_args.kwargs["context_version"] == 9
    assert refresh_mock.call_args.kwargs["artefact_type"] == "pmp"


def test_update_pmp_prompt_orders_static_and_volatile_content() -> None:
    from datetime import date

    from app.workflows.update_pmp import build_update_pmp_prompt
    from tests.workflows.test_create_pmp import _passage

    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/commercial-construction-guide.md",
        whole_document=True,
        content="Seed guidance content for commercial construction.",
    )
    delta_passage = _passage(
        project="taxonomy-project",
        source_type="project_evidence",
        relative_path="04-projects/taxonomy-project/_inbox/tenant-brief.md",
        whole_document=True,
        content="Tenant brief evidence content.",
    )
    pmp_context = build_pmp_context(_generation_context())
    generation_brief = build_generation_brief(
        pmp_context,
        evidence_refs=[
            "project_evidence:04-projects/taxonomy-project/_inbox/tenant-brief.md"
        ],
        seed_refs=["platform_knowledge:seed/commercial-construction-guide.md"],
        constraints=["Preserve human-controlled blocks during refresh."],
    )
    prompt = build_update_pmp_prompt(
        project=_taxonomy_project(),
        baseline=_baseline_draft(),
        delta_passages=[delta_passage],
        platform_passages=[platform_passage],
        run_date=date(2026, 7, 8),
        validation_feedback="Fix the missing risk register.",
        coverage_requirements="- tenant-brief.md\n  - programme date: 1 November 2026",
        pmp_context=pmp_context,
        generation_brief=generation_brief,
    )

    platform_index = prompt.index("Seed guidance content for commercial construction.")
    title_index = prompt.index("Residential House")
    date_index = prompt.index("2026-07-08")
    baseline_index = prompt.index("Baseline revision: v1")
    coverage_index = prompt.index("Mandatory current-corpus coverage")
    evidence_index = prompt.index("Tenant brief evidence content.")
    feedback_index = prompt.index("Fix the missing risk register.")

    assert platform_index < title_index
    assert title_index < date_index
    assert (
        date_index < baseline_index < coverage_index < evidence_index < feedback_index
    )
    assert generation_brief.input_fingerprint in prompt


@pytest.mark.parametrize(
    "use_corpus_sweep",
    (True, False),
    ids=("corpus-sweep", "evidence-delta"),
)
def test_update_pmp_bounds_corpus_and_delta_evidence_before_generation(
    monkeypatch: pytest.MonkeyPatch,
    use_corpus_sweep: bool,
) -> None:
    from tests.workflows.test_create_pmp import _passage

    project = _taxonomy_project(
        building_class="residential" if use_corpus_sweep else None
    )
    baseline = _baseline_draft()
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    created_draft = DraftArtifact(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=2,
        status="draft",
        title="Project Management Plan",
        workspace_path=baseline.workspace_path,
        author_user_id=USER_ID,
        content_markdown=baseline.content_markdown,
        model="gpt-5.6-terra",
        runtime="clerk-sitewise-update-pmp",
        provenance_metadata={},
        created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )

    active_passage = _passage(
        project="taxonomy-project",
        source_type="project_evidence",
        relative_path="04-projects/taxonomy-project/_inbox/tenant-brief.md",
        whole_document=True,
        content=(
            "This tenant requirements brief lists functional requirements.\n"
            "Target possession for fit-out: 1 November 2026.\n"
            "Fit-out includes 42 workstations.\n"
            + "Additional unselected detail. "
            * 40
        ),
    )
    overflow_passage = _passage(
        project="taxonomy-project",
        source_type="project_evidence",
        relative_path="04-projects/taxonomy-project/_inbox/overflow-brief.md",
        whole_document=True,
        content="This second project document must be excluded by the global budget.",
    )
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/procurement-tendering-guide.md",
        whole_document=True,
        content="Mandatory platform guidance for controlled project updates.",
    )
    sweep_refs = tuple(
        f"project_evidence:{passage.relative_path}#chunk={passage.chunk_id}"
        for passage in (active_passage, overflow_passage)
    )
    sweep_result = SimpleNamespace(
        passages=(active_passage, overflow_passage),
        merged_pack=SimpleNamespace(evidence_refs=list(sweep_refs)),
        evidence_refs=sweep_refs,
        listing=SimpleNamespace(
            documents=(active_passage, overflow_passage),
            total_indexed=2,
            skipped_superseded=0,
            skipped_revision_duplicate=0,
            capped=False,
        ),
        trace_events=(),
    )
    update_budget = RetrievalBudget(
        max_searches=1,
        max_chunks=2,
        max_documents=2,
        max_tokens=48,
        max_chars=360,
        max_concurrency=1,
    )
    monkeypatch.setattr(
        "app.workflows.update_pmp.UPDATE_PMP_RETRIEVAL_BUDGET",
        update_budget,
        raising=False,
    )
    run_model = AsyncMock(
        return_value=PmpDraftOutput(
            title="Project Management Plan",
            markdown=baseline.content_markdown,
            seed_consulted=_valid_seed_consulted()
            + ["seed/new-dwelling-guide.md", "seed/role-architect-pm.md"],
            evidence_refs=[],
            context_refs=["doctrine:docs/clerk-brief.md"],
        )
    )

    with (
        patch(
            "app.workflows.update_pmp.overlay_status",
            return_value=overlay_status(
                archetype="new-dwelling",
                state="NSW",
            ),
        ),
        patch(
            "app.workflows.update_pmp.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.update_pmp.get_latest_draft_artifact",
            new=AsyncMock(return_value=baseline),
        ),
        patch(
            "app.workflows.update_pmp.retrieve_create_pmp_sources",
            new=AsyncMock(
                return_value=(
                    [platform_passage],
                    0,
                    1,
                    "platform_seeded",
                    [],
                )
            ),
        ),
        patch(
            "app.workflows.update_pmp.sweep_current_pmp_corpus",
            new=AsyncMock(return_value=sweep_result),
        ) as sweep_mock,
        patch(
            "app.workflows.create_pmp.retrieve_project_evidence_delta",
            new=AsyncMock(return_value=[active_passage, overflow_passage]),
        ) as delta_mock,
        patch("app.workflows.update_pmp.run_update_pmp_model", new=run_model),
        patch(
            "app.workflows.update_pmp.validate_update_pmp_output",
            return_value=None,
        ),
        patch(
            "app.workflows.update_pmp.create_draft_artifact",
            new=AsyncMock(return_value=created_draft),
        ) as create_draft_mock,
        patch("app.workflows.create_pmp.sync_pmp_draft_workspace", new=AsyncMock()),
        patch("app.workflows.update_pmp.sync_decisions_from_markdown", new=AsyncMock()),
        patch("app.workflows.update_pmp._persist_trace_message", new=AsyncMock()),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=2),
        ),
    ):
        response = run_async(
            run_update_pmp_workflow(
                session,
                user_id=USER_ID,
                project=project,
                thread_id=None,
                generation_context=_generation_context(),
            )
        )

    assert response.status == "complete"
    assert run_model.await_count == 1
    selected_passages = run_model.await_args.kwargs["delta_passages"]
    assert len(selected_passages) == 1
    assert selected_passages[0].relative_path == active_passage.relative_path
    assert len(selected_passages[0].content) <= update_budget.max_chars
    assert selected_passages[0].content != active_passage.content
    selected_platform = run_model.await_args.kwargs["platform_passages"]
    assert [item.relative_path for item in selected_platform] == [
        platform_passage.relative_path
    ]
    assert sum(
        len(item.content) for item in [*selected_platform, *selected_passages]
    ) <= update_budget.max_chars
    generation_brief = run_model.await_args.kwargs["generation_brief"]
    assert generation_brief.evidence_refs == (sweep_refs[0],)
    if use_corpus_sweep:
        sweep_mock.assert_awaited_once()
        delta_mock.assert_not_awaited()
    else:
        sweep_mock.assert_not_awaited()
        delta_mock.assert_awaited_once()
    advisory = next(event for event in response.trace if event.step == "coverage")
    assert advisory.status == "advisory"
    saved_markdown = create_draft_mock.await_args.kwargs["content_markdown"]
    assert "Evidence coverage register" not in saved_markdown
    assert "| Section | Evidence status | Citation |" not in saved_markdown


@pytest.mark.anyio
async def test_sweep_respects_config_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "pmp_sweep_max_documents", 5)
    docs = [
        SimpleNamespace(
            id=uuid.uuid4(),
            project="demo-project",
            phase="brief-planning",
            source_type="project_evidence",
            document_class="brief",
            filename=f"doc-{index}.md",
            relative_path=f"04-projects/demo/doc-{index}.md",
            normalized_content="Fee proposal content",
            document_metadata=None,
            updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        for index in range(10)
    ]
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: docs)
            )
        )
    )
    project = SimpleNamespace(id=PROJECT_ID, slug="demo-project")
    result = await sweep_current_pmp_corpus(
        session, project=project, previous_evidence_refs=[]
    )
    assert len(result.listing.documents) == 5
    assert result.listing.capped is True
    assert any(event.status == "warning" for event in result.trace_events)
