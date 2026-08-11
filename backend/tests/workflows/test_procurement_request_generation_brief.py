from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Literal

import pytest

from app.projects.artefact_context import RfpContext, RftContext
from app.projects.generation_brief import ArtefactGenerationBrief
from app.projects.generation_context import ProjectGenerationContext
from app.workflows import procurement_request as workflow


PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@dataclass(frozen=True, slots=True)
class _Target:
    name: str
    slug: str


class _NoSearchRetriever:
    async def retrieve(self, query: str, **kwargs: Any) -> list[Any]:
        del query, kwargs
        raise AssertionError("complete structured context must not search")


class _Document(workflow.ProcurementDocument):
    workspace_subfolder = "02-procurement"
    filename_stem = "request"
    runtime_name = "test-procurement"
    trace_tool_name = "test_procurement"
    trace_generation_purpose = "test generation"
    trace_evidence_purpose = "test evidence"
    trace_guidance_purpose = "test guidance"

    def __init__(
        self,
        artefact_type: Literal["rfp", "rft"],
        issued_paths: tuple[str, ...],
        consistency_call_counts: tuple[int, ...] = (),
    ) -> None:
        self.seed_artefact_type = artefact_type
        self.document_key = artefact_type
        self.knowledge_workflow = (
            "consultant-procurement" if artefact_type == "rfp" else "trade-procurement"
        )
        self.target = (
            _Target("Structural Engineer", "structural-engineer")
            if artefact_type == "rfp"
            else _Target("Mechanical Services", "mechanical-services")
        )
        self.issued_paths = issued_paths
        self.consistency_call_counts = consistency_call_counts
        self.rendered_brief: ArtefactGenerationBrief | None = None

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
    ) -> RfpContext | RftContext:
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
        return RftContext(
            package=target.name,
            known_exclusions={},
            **common,
        )

    async def issued_documents(
        self,
        session: Any,
        *,
        project: Any,
        target: workflow.ProcurementTarget,
        narrative_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del session, project, target, narrative_evidence
        return [{"relative_path": path} for path in self.issued_paths]

    async def forecast(
        self,
        session: Any,
        *,
        project_id: uuid.UUID,
        target: workflow.ProcurementTarget,
    ) -> dict[str, Any]:
        del session, project_id, target
        return {}

    def assumptions_and_missing(
        self,
        *,
        project: Any,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: workflow.ProcurementTarget,
    ) -> tuple[list[str], list[str]]:
        del project, evidence, forecast, target
        return [], []

    def render(self, **kwargs: Any) -> str | Awaitable[str]:
        self.rendered_brief = kwargs["generation_brief"]

        async def rendered() -> str:
            for call_count in self.consistency_call_counts:
                await kwargs["on_progress"](
                    {
                        "stage": "consistency_complete",
                        "ai_call_count": call_count,
                    }
                )
            return (
                "# Procurement request\n\n## Background\n\nIssue the documented scope."
            )

        return (
            rendered()
            if self.consistency_call_counts
            else (
                "# Procurement request\n\n## Background\n\nIssue the documented scope."
            )
        )


@pytest.mark.parametrize("artefact_type", ["rfp", "rft"])
def test_procurement_attempt_persists_one_exact_brief_with_issued_register(
    monkeypatch: pytest.MonkeyPatch,
    artefact_type: Literal["rfp", "rft"],
) -> None:
    built_briefs: list[ArtefactGenerationBrief] = []
    real_build = workflow.build_generation_brief

    def record_build(*args: Any, **kwargs: Any) -> ArtefactGenerationBrief:
        brief = real_build(*args, **kwargs)
        built_briefs.append(brief)
        return brief

    monkeypatch.setattr(workflow, "build_generation_brief", record_build)
    first_path = "04-projects/demo/03-design/issued-a.pdf"
    second_path = "04-projects/demo/03-design/issued-b.pdf"
    first_document = _Document(artefact_type, (first_path, first_path))
    second_document = _Document(artefact_type, (second_path,))

    first_result = _run_attempt(first_document)
    second_result = _run_attempt(second_document)

    assert len(built_briefs) == 2
    for index, (document, result, expected_path) in enumerate(
        (
            (first_document, first_result, first_path),
            (second_document, second_result, second_path),
        )
    ):
        brief = document.rendered_brief
        assert brief is built_briefs[index]
        assert brief.evidence_refs == (expected_path,)
        persisted = result.draft.provenance_metadata
        brief_dump = brief.model_dump(mode="json")
        assert brief.seed_refs == tuple(persisted["context_refs"])
        assert persisted["generation_brief"] == brief_dump
        assert persisted["generation_manifest"]["generation_brief"] == brief_dump
        assert (
            persisted["generation_manifest"]["input_fingerprint"]
            == brief.input_fingerprint
        )
    assert built_briefs[0].input_fingerprint != built_briefs[1].input_fingerprint


def test_procurement_attempt_persists_consistency_calls_from_all_attempts() -> None:
    document = _Document(
        "rfp",
        ("04-projects/demo/03-design/issued.pdf",),
        consistency_call_counts=(1, 0, 1),
    )

    result = _run_attempt(document)

    assert result.source_trace["consistency_ai_call_count"] == 2
    assert (
        result.draft.provenance_metadata["source_trace"]["consistency_ai_call_count"]
        == 2
    )


def _run_attempt(document: _Document):
    async def next_version(session: Any, **kwargs: Any) -> int:
        del session, kwargs
        return 1

    async def create_draft(session: Any, **kwargs: Any):
        del session
        return SimpleNamespace(
            id=DRAFT_ID,
            version=1,
            **kwargs,
        )

    async def sync_workspace(session: Any, **kwargs: Any) -> str:
        del session
        return str(kwargs["draft"].workspace_path)

    async def no_baseline(session: Any, **kwargs: Any):
        del session, kwargs
        return None

    return asyncio.run(
        workflow.draft_procurement_request(
            SimpleNamespace(),
            project=SimpleNamespace(
                id=PROJECT_ID,
                workspace_path="04-projects/demo",
            ),
            user_id=USER_ID,
            document=document,
            raw_target=document.target.name,
            generation_context=_generation_context(),
            auto_commit=False,
            retriever_factory=lambda session: _NoSearchRetriever(),
            next_version=next_version,
            create_draft=create_draft,
            sync_workspace=sync_workspace,
            get_baseline_draft=no_baseline,
        )
    )


def _generation_context() -> ProjectGenerationContext:
    return ProjectGenerationContext(
        project_id=PROJECT_ID,
        context_version=7,
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
