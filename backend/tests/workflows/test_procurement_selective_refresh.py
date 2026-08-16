"""F7: baseline-aware RFP/RFT selective refresh."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Literal
from unittest.mock import AsyncMock

import pytest

from app.projects.generation_context import ProjectGenerationContext
from app.projects.selective_refresh import compute_refresh_input_hash
from app.workflows import procurement_request as workflow


PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
BASELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DRAFT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


@dataclass(frozen=True, slots=True)
class _Target:
    name: str
    slug: str


class _NoSearchRetriever:
    async def retrieve(self, query: str, **kwargs: Any) -> list[Any]:
        del query, kwargs
        raise AssertionError("unchanged refresh must not search")


class _Document(workflow.ProcurementDocument):
    workspace_subfolder = "02-procurement"
    filename_stem = "request"
    runtime_name = "test-procurement"
    trace_tool_name = "test_procurement"
    trace_generation_purpose = "test generation"
    trace_evidence_purpose = "test evidence"
    trace_guidance_purpose = "test guidance"

    def __init__(self, artefact_type: Literal["rfp", "rft"]) -> None:
        self.seed_artefact_type = artefact_type
        self.document_key = artefact_type
        self.knowledge_workflow = (
            "consultant-procurement" if artefact_type == "rfp" else "trade-procurement"
        )
        self.target = _Target("Hydraulic Engineer", "hydraulic_engineer")
        self.render_calls = 0

    def resolve_target(self, raw: str) -> _Target:
        del raw
        return self.target

    def title(self, target: workflow.ProcurementTarget) -> str:
        return f"{self.seed_artefact_type.upper()} - {target.name}"

    def evidence_queries(
        self, target: workflow.ProcurementTarget
    ) -> tuple[workflow.EvidenceQuery, ...]:
        del target
        return ()

    def platform_query(self, target: workflow.ProcurementTarget) -> str:
        return f"{target.name} procurement guidance"

    def platform_guidance_paths(
        self, target: workflow.ProcurementTarget
    ) -> tuple[str, ...]:
        del target
        return ()

    def build_context(
        self,
        project_context: ProjectGenerationContext,
        target: workflow.ProcurementTarget,
    ):
        from app.projects.artefact_context import RfpContext, RftContext

        common = {
            "project_id": project_context.project_id,
            "context_version": project_context.context_version,
            "identity": {},
            "taxonomy": {},
            "scope": {},
            "scale": {},
            "complexity": {},
            "programme": {},
            "procurement": {},
            "approvals": {},
            "critical_unknowns": [],
        }
        if self.seed_artefact_type == "rfp":
            return RfpContext(
                discipline=target.name,
                stakeholders={},
                derived_risks=[],
                section_weights={},
                **common,
            )
        return RftContext(package=target.name, known_exclusions={}, **common)

    async def issued_documents(self, session: Any, **kwargs: Any) -> list[dict[str, Any]]:
        del session, kwargs
        return []

    async def forecast(self, session: Any, **kwargs: Any) -> dict[str, Any]:
        del session, kwargs
        return {}

    def assumptions_and_missing(self, **kwargs: Any) -> tuple[list[str], list[str]]:
        del kwargs
        return [], []

    def render(self, **kwargs: Any) -> str | Awaitable[str]:
        del kwargs
        self.render_calls += 1
        return (
            "# Procurement request\n\n"
            "## Background\n\n"
            "Hydraulic scope for the project.\n\n"
            "## Scope\n\n"
            "- Design services\n\n"
            "## Citation key\n\n"
            "[1] Project Profile — current\n"
        )


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        id=PROJECT_ID,
        workspace_path="04-projects/demo",
        archetype="new-dwelling",
        project_context_version=3,
        building_class=None,
        work_type=None,
        project_metadata={},
    )


def _generation_context(version: int = 3) -> ProjectGenerationContext:
    return ProjectGenerationContext(
        project_id=PROJECT_ID,
        context_version=version,
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


def _refresh_hash(document: _Document, *, context_version: int = 3) -> str:
    seed = workflow._select_procurement_seed_knowledge(
        document=document,
        project=_project(),
        target=document.target,
        generation_context=_generation_context(context_version),
    )
    return compute_refresh_input_hash(
        context_version=context_version,
        source_version=f"instructions:|pages:1|target:{document.target.slug}",
        seed_version="|".join(seed.applicable_paths) or "no-seed-guidance",
        artefact_type=document.seed_artefact_type,
    )


@pytest.mark.parametrize("artefact_type", ["rfp", "rft"])
def test_procurement_unchanged_refresh_skips_retrieval_and_render(
    artefact_type: Literal["rfp", "rft"],
) -> None:
    document = _Document(artefact_type)
    baseline_md = (
        "# Procurement request\n\n"
        "## Background\n\n"
        "Hydraulic scope for the project.\n\n"
        "## Citation key\n\n"
        "[1] Project Profile — current\n"
    )
    baseline = SimpleNamespace(
        id=BASELINE_ID,
        version=2,
        content_markdown=baseline_md,
        provenance_metadata={
            "incremental_update": {"input_hash": _refresh_hash(document)},
            "blocks": {},
        },
        workspace_path="04-projects/demo/02-procurement/request_hydraulic_engineer_v02.draft.md",
    )
    get_latest = AsyncMock(return_value=baseline)
    create_draft = AsyncMock(side_effect=AssertionError("must not create draft"))

    result = asyncio.run(
        workflow.draft_procurement_request(
            SimpleNamespace(),
            project=_project(),
            user_id=USER_ID,
            document=document,
            raw_target=document.target.name,
            generation_context=_generation_context(),
            auto_commit=False,
            retriever_factory=lambda session: _NoSearchRetriever(),
            create_draft=create_draft,
            sync_workspace=AsyncMock(),
            get_baseline_draft=get_latest,
        )
    )

    assert result.draft.id == BASELINE_ID
    assert document.render_calls == 0
    create_draft.assert_not_awaited()
    assert result.source_trace.get("selective_refresh") == "skipped"


@pytest.mark.parametrize("artefact_type", ["rfp", "rft"])
def test_procurement_legacy_scaffold_does_not_skip_even_when_hash_matches(
    artefact_type: Literal["rfp", "rft"],
) -> None:
    document = _Document(artefact_type)
    baseline_md = (
        "# Request for Fee Proposal - Hydraulic Engineer\n\n"
        "## Project Summary\n"
        "| Field | Project detail | Source |\n"
        "| --- | --- | --- |\n"
        "| Project | Demo | Profile |\n"
    )
    baseline = SimpleNamespace(
        id=BASELINE_ID,
        version=3,
        content_markdown=baseline_md,
        provenance_metadata={
            "incremental_update": {"input_hash": _refresh_hash(document)},
            "blocks": {},
        },
        workspace_path="04-projects/demo/02-procurement/request_hydraulic_engineer_v03.draft.md",
    )
    created: dict[str, Any] = {}

    async def create_draft(session: Any, **kwargs: Any):
        del session
        created.update(kwargs)
        return SimpleNamespace(id=DRAFT_ID, version=4, **kwargs)

    result = asyncio.run(
        workflow.draft_procurement_request(
            SimpleNamespace(),
            project=_project(),
            user_id=USER_ID,
            document=document,
            raw_target=document.target.name,
            generation_context=_generation_context(),
            auto_commit=False,
            retriever_factory=lambda session: _NoSearchRetriever(),
            next_version=AsyncMock(return_value=4),
            create_draft=create_draft,
            sync_workspace=AsyncMock(return_value="path"),
            get_baseline_draft=AsyncMock(return_value=baseline),
        )
    )

    assert document.render_calls == 1
    assert result.draft.id == DRAFT_ID
    assert "## Citation key" in created["content_markdown"]
    assert "Profile" not in created["content_markdown"].split("## Citation key")[0]
    assert result.source_trace.get("selective_refresh") != "skipped"


def test_legacy_procurement_scaffold_detects_fee_proposal_shell() -> None:
    legacy = (
        "# Request for Fee Proposal - Structural engineer\n\n"
        "## Project Summary\n"
        "| Field | Project detail | Source |\n"
        "| --- | --- | --- |\n"
        "| Project | Petersham | Profile |\n"
    )
    modern = (
        "# Request for Proposal - Structural engineer\n\n"
        "## Project summary\n"
        "| Project | Petersham | [1] |\n"
        "| --- | --- | --- |\n\n"
        "## Citation key\n\n"
        "[1] Project Profile — current\n"
    )
    assert workflow._legacy_procurement_scaffold(legacy) is True
    assert workflow._legacy_procurement_scaffold(modern) is False


@pytest.mark.parametrize("artefact_type", ["rfp", "rft"])
def test_procurement_refresh_reconciles_baseline_and_persists_audit(
    artefact_type: Literal["rfp", "rft"],
) -> None:
    document = _Document(artefact_type)
    baseline_md = (
        "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"
        "User-controlled background note.\n\n"
        "## Scope\n\n"
        "- Design services <!-- clerk:block id=blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -->\n\n"
        "## Citation key\n\n"
        "[1] Project Profile — current\n"
    )
    baseline = SimpleNamespace(
        id=BASELINE_ID,
        version=1,
        content_markdown=baseline_md,
        provenance_metadata={
            "blocks": {
                "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {
                    "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "type": "paragraph",
                    "created_by": "user",
                    "last_modified_by": "user",
                    "created_at": "2026-08-10T00:00:00+00:00",
                    "updated_at": "2026-08-10T00:00:00+00:00",
                    "baseline_content_hash": "old",
                    "user_protected": False,
                    "status": "active",
                },
                "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": {
                    "id": "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "type": "list_item",
                    "created_by": "ai",
                    "last_modified_by": "ai",
                    "created_at": "2026-08-10T00:00:00+00:00",
                    "updated_at": "2026-08-10T00:00:00+00:00",
                    "baseline_content_hash": "ai-hash",
                    "user_protected": False,
                    "status": "active",
                },
            }
        },
    )
    created: dict[str, Any] = {}

    async def create_draft(session: Any, **kwargs: Any):
        del session
        created.update(kwargs)
        return SimpleNamespace(id=DRAFT_ID, version=2, **kwargs)

    result = asyncio.run(
        workflow.draft_procurement_request(
            SimpleNamespace(),
            project=_project(),
            user_id=USER_ID,
            document=document,
            raw_target=document.target.name,
            generation_context=_generation_context(version=4),
            auto_commit=False,
            retriever_factory=lambda session: _NoSearchRetriever(),
            next_version=AsyncMock(return_value=2),
            create_draft=create_draft,
            sync_workspace=AsyncMock(return_value="path"),
            get_baseline_draft=AsyncMock(return_value=baseline),
        )
    )

    assert document.render_calls == 1
    assert result.draft.id == DRAFT_ID
    provenance = created["provenance_metadata"]
    assert "User-controlled background note." in created["content_markdown"]
    assert provenance["blocks"]["blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]["status"] in {
        "propose_delete",
        "conflict",
        "active",
    }
    assert "proposed_delete" in provenance["incremental_update"]
    assert provenance["incremental_update"]["input_hash"]
    assert provenance["based_on_draft_id"] == str(BASELINE_ID)
