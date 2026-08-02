from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.workflows import procurement_request as engine
from app.workflows import trade_procurement as workflow
from app.workflows.rfp_narrative import ProcurementNarrativeOutput
from tests.conftest import run_async
from tests.workflows.test_consultant_procurement import (
    DRAFT_ID,
    USER_ID,
    _Session,
    _StubRetriever,
    _passage,
    _project,
)


def _install(monkeypatch, *, retriever: _StubRetriever, version: int = 1) -> None:
    monkeypatch.setattr(engine, "DocumentRetriever", lambda session: retriever)
    monkeypatch.setattr(engine, "next_draft_version", AsyncMock(return_value=version))
    monkeypatch.setattr(engine, "load_sections", AsyncMock(return_value=None))

    async def _create_draft(session, **kwargs):
        return SimpleNamespace(
            id=DRAFT_ID,
            project_id=kwargs["project_id"],
            workflow_type=kwargs["workflow_type"],
            version=version,
            status="draft",
            title=kwargs["title"],
            workspace_path=kwargs["workspace_path"],
            author_user_id=kwargs["author_user_id"],
            content_markdown=kwargs["content_markdown"],
            model=kwargs["model"],
            runtime=kwargs["runtime"],
            provenance_metadata=kwargs["provenance_metadata"],
        )

    monkeypatch.setattr(engine, "create_draft_artifact", AsyncMock(side_effect=_create_draft))

    async def _sync(session, *, project, draft, markdown=None):
        kind, target_slug = workflow._workflow_parts(draft.workflow_type)
        draft.workspace_path = workflow.trade_procurement_workspace_path(
            project,
            kind=kind,
            target_slug=target_slug,
            version=draft.version,
        )
        return draft.workspace_path

    monkeypatch.setattr(workflow, "sync_trade_procurement_draft_workspace", _sync)

    async def _narrative(**kwargs):
        evidence = kwargs["project_evidence"]
        if not evidence:
            return ProcurementNarrativeOutput(
                background="Confirm the project scope and issued information before issue."
            )
        token = kwargs["citation_index"].token_for(evidence[0]["relative_path"])
        return ProcurementNarrativeOutput(
            background=f"The issued information defines the package basis. {token}",
            requested_services=[
                f"Coordinate the package with the documented project scope. {token}"
            ],
            programme=[f"Confirm the documented programme constraints. {token}"],
        )

    monkeypatch.setattr(workflow, "run_procurement_narrative_model", _narrative)


def _draft(monkeypatch, *, package: str, kind: str, max_pages: int = 3):
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content="The project includes documented building works.",
                    metadata={
                        "document_number": "A001",
                        "title": "Project brief",
                        "revision": "P1",
                        "discipline": "Architectural",
                    },
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever)
    return run_async(
        workflow.draft_trade_procurement_artifact(
            _Session(),
            project=_project(),
            user_id=USER_ID,
            package=package,
            kind=kind,
            max_pages=max_pages,
        )
    )


def test_trade_aliases_resolve_to_one_profile() -> None:
    windows = workflow.normalise_trade_target("aluminium windows")
    glazing = workflow.normalise_trade_target("glazing")

    assert windows.slug == "windows_and_glazing"
    assert glazing == windows


def test_unknown_trade_uses_safe_generic_profile() -> None:
    profile = workflow.normalise_trade_target("Aquarium glazing")

    assert profile.name == "Aquarium glazing"
    assert profile.slug == "aquarium_glazing"
    assert "Confirm the in-scope Aquarium glazing work" in profile.baseline_scope[0]
    assert "certification" in profile.baseline_scope[-1]


def test_structural_steel_rft_generates_deterministic_controls(monkeypatch) -> None:
    result = _draft(monkeypatch, package="structural steel", kind="rft")

    markdown = result.draft.content_markdown
    assert result.kind == "rft"
    assert result.draft.title == "Request for Tender - Structural Steel"
    assert result.draft.workflow_type == "trade_rft_structural_steel"
    assert result.draft.workspace_path.endswith(
        "/05-procurement/structural_steel/02-tender-pack/structural_steel_rft_v01.draft.md"
    )
    assert "## Project Summary" in markdown
    assert "## Scope and interfaces" in markdown
    assert "## Price schedule" in markdown
    assert "## Tender conditions and RFI process" in markdown
    assert "| **Tender / quotation total** | Subject to stated qualifications | **TBC** | **TBC** | **TBC** |" in markdown
    assert result.draft.provenance_metadata["request_kind"] == "rft"
    assert result.draft.provenance_metadata["trade_package"] == "Structural Steel"


def test_electrical_rfq_is_complete_without_a_hard_page_cap(monkeypatch) -> None:
    result = _draft(monkeypatch, package="electrician", kind="rfq", max_pages=5)

    markdown = result.draft.content_markdown
    assert result.kind == "rfq"
    assert result.draft.title == "Request for Quotation - Electrical Services"
    assert result.draft.provenance_metadata["max_pages"] == 5
    assert "## Price schedule" in markdown
    assert "## Returnables" in markdown
    assert "## Quotation conditions" in markdown
    assert "Tender conditions and RFI process" not in markdown
    assert "## Review items before issue" in markdown


@pytest.mark.parametrize("kind", ["", "quote", "tender"])
def test_trade_kind_is_validated(monkeypatch, kind: str) -> None:
    with pytest.raises(ValueError, match="kind must be rft or rfq"):
        _draft(monkeypatch, package="Electrical", kind=kind)


def test_trade_narrative_retries_invalid_citation(monkeypatch) -> None:
    profile = workflow.normalise_trade_target("electrical")
    evidence = [{"relative_path": "docs/brief.pdf"}]
    citation_index = workflow.build_rfp_citation_index(evidence)
    invalid = ProcurementNarrativeOutput(
        background="The brief defines the package. [99]",
        requested_services=["Provide the package scope. [1]"],
    )
    valid = ProcurementNarrativeOutput(
        background="The brief defines the package. [1]",
        requested_services=["Provide the package scope. [1]"],
    )
    run_model = AsyncMock(side_effect=[invalid, valid])
    monkeypatch.setattr(workflow, "run_procurement_narrative_model", run_model)

    result = run_async(
        workflow.run_validated_trade_narrative(
            project=_project(),
            target=profile,
            kind="rfq",
            project_evidence=evidence,
            platform_knowledge=[],
            citation_index=citation_index,
        )
    )

    assert result == valid
    assert run_model.await_count == 2
    assert "[99]" in run_model.await_args_list[1].kwargs["validation_feedback"]
