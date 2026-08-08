import uuid
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


def _install(
    monkeypatch,
    *,
    retriever: _StubRetriever,
    version: int = 1,
    package_evidence: list[dict] | None = None,
) -> None:
    monkeypatch.setattr(engine, "DocumentRetriever", lambda session: retriever)
    monkeypatch.setattr(engine, "next_draft_version", AsyncMock(return_value=version))
    monkeypatch.setattr(engine, "load_sections", AsyncMock(return_value=None))
    monkeypatch.setattr(
        workflow,
        "load_trade_package_evidence",
        AsyncMock(return_value=package_evidence or []),
    )

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

    monkeypatch.setattr(
        engine, "create_draft_artifact", AsyncMock(side_effect=_create_draft)
    )

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
    assert "Define the in-scope Aquarium glazing work" in profile.baseline_scope[0]
    assert "certification" in profile.baseline_scope[-1]


def test_package_loader_selects_all_primary_trade_design_documents() -> None:
    documents = [
        SimpleNamespace(
            id=uuid.uuid4(),
            filename="M01 - Mechanical Design & Spec - 01 Electrical [C].pdf",
            relative_path="04-projects/demo/_inbox/M01.pdf",
            document_class="specification",
            document_metadata={
                "document_number": "M01",
                "title": "Electrical",
                "revision": "C",
                "discipline": "Electrical",
            },
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            filename="M02 - Mechanical Design & Spec - 02 Flexible [C].pdf",
            relative_path="04-projects/demo/_inbox/M02.pdf",
            document_class="specification",
            document_metadata={
                "document_number": "M02",
                "title": "Flexible connections",
                "revision": "C",
                "discipline": "Mechanical",
            },
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            filename="CC-A-182 RCP - LEVEL 1.pdf",
            relative_path="04-projects/demo/03-design/architect/CC-A-182.pdf",
            document_class="drawing",
            document_metadata={"discipline": "Architectural"},
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            filename="Mechanical Design Certificate.pdf",
            relative_path="04-projects/demo/_inbox/mechanical-certificate.pdf",
            document_class="certificate",
            document_metadata={"discipline": "Mechanical"},
        ),
    ]
    result = SimpleNamespace(all=lambda: documents)
    session = _Session()
    session.execute = AsyncMock(return_value=result)

    evidence = run_async(
        workflow.load_trade_package_evidence(
            session,
            project_id=_project().id,
            target=workflow.normalise_trade_target("mechanical contractor"),
        )
    )

    assert [item["relative_path"] for item in evidence] == [
        "04-projects/demo/_inbox/M01.pdf",
        "04-projects/demo/_inbox/M02.pdf",
    ]
    assert all(
        item["document_metadata"]["discipline"] == "Mechanical" for item in evidence
    )


def test_structural_steel_rft_generates_deterministic_controls(monkeypatch) -> None:
    result = _draft(monkeypatch, package="structural steel", kind="rft")

    markdown = result.draft.content_markdown
    assert result.kind == "rft"
    assert result.draft.title == "Request for Tender - Structural Steel"
    assert result.draft.workflow_type == "trade_rft_structural_steel"
    assert result.draft.workspace_path.endswith(
        "/05-procurement/structural_steel/02-tender-pack/structural_steel_rft_v01.draft.md"
    )
    assert "## Tender particulars" in markdown
    assert "## Scope and interfaces" in markdown
    assert "## Price schedule" in markdown
    assert "**Tender conditions and RFI process**" in markdown
    dash = chr(0x2014)
    assert (
        f"| **Tender total** | Subject to stated qualifications | **{dash}** | "
        f"**{dash}** | **{dash}** |" in markdown
    )
    primary = markdown.split("## Trace & QA", maxsplit=1)[0]
    assert "TBC" not in primary
    assert "Confirm" not in primary
    assert result.draft.provenance_metadata["request_kind"] == "rft"
    assert result.draft.provenance_metadata["trade_package"] == "Structural Steel"


def test_mechanical_rft_includes_every_primary_trade_sheet_and_marks_it_used(
    monkeypatch,
) -> None:
    package_evidence = [
        {
            "role": "package_document",
            "role_label": "Mechanical package document",
            "document_id": f"document-{number}",
            "chunk_id": f"document-{number}",
            "filename": f"{number} - Mechanical Design.pdf",
            "relative_path": f"04-projects/walsh-renovation/_inbox/{number}.pdf",
            "page_or_section": None,
            "snippet": f"Mechanical drawing register entry {number}.",
            "score": None,
            "document_metadata": {
                "document_number": number,
                "title": f"Mechanical sheet {number}",
                "revision": "C",
                "discipline": "Mechanical",
            },
        }
        for number in ("M01", "M02", "M10")
    ]
    retriever = _StubRetriever()
    _install(
        monkeypatch,
        retriever=retriever,
        package_evidence=package_evidence,
    )

    result = run_async(
        workflow.draft_trade_procurement_artifact(
            _Session(),
            project=_project(),
            user_id=USER_ID,
            package="mechanical contractor",
            kind="rft",
        )
    )

    markdown = result.draft.content_markdown
    assert "| M01 | Mechanical sheet M01 | C | Mechanical | [1] |" in markdown
    assert "| M02 | Mechanical sheet M02 | C | Mechanical | [2] |" in markdown
    assert "| M10 | Mechanical sheet M10 | C | Mechanical | [3] |" in markdown
    assert result.draft.provenance_metadata["evidence_refs"] == [
        "04-projects/walsh-renovation/_inbox/M01.pdf",
        "04-projects/walsh-renovation/_inbox/M02.pdf",
        "04-projects/walsh-renovation/_inbox/M10.pdf",
    ]


def test_trade_scope_strips_model_supplied_list_numbers(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="brief.pdf",
                    path="04-projects/walsh-renovation/brief.pdf",
                    content="Mechanical package basis.",
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever)
    monkeypatch.setattr(
        workflow,
        "run_procurement_narrative_model",
        AsyncMock(
            return_value=ProcurementNarrativeOutput(
                background="The brief defines the package. [1]",
                requested_services=[
                    "1. Supply and install the mechanical works. [1]",
                    "2. Coordinate all trade interfaces. [1]",
                ],
            )
        ),
    )

    result = run_async(
        workflow.draft_trade_procurement_artifact(
            _Session(),
            project=_project(),
            user_id=USER_ID,
            package="mechanical contractor",
            kind="rft",
        )
    )

    scope = result.draft.content_markdown.split("## Scope and interfaces", maxsplit=1)[
        1
    ].split("## Information to review", maxsplit=1)[0]
    assert "1. Supply and install the mechanical works. [1]" in scope
    assert "2. Coordinate all trade interfaces. [1]" in scope
    assert "1. 1." not in scope
    assert "2. 2." not in scope


def test_legacy_rfq_input_creates_the_universal_rft(monkeypatch) -> None:
    result = _draft(monkeypatch, package="electrician", kind="rfq", max_pages=5)

    markdown = result.draft.content_markdown
    assert result.kind == "rft"
    assert result.draft.title == "Request for Tender - Electrical Services"
    assert result.draft.workflow_type == "trade_rft_electrical_services"
    assert result.draft.provenance_metadata["max_pages"] == 5
    assert "## Price schedule" in markdown
    assert "**Returnables**" in markdown
    assert "**Tender conditions and RFI process**" in markdown
    assert "Request for Quotation" not in markdown
    assert "## Trace & QA" in markdown


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
