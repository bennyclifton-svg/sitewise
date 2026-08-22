"""X1 Stage 20: user-approved cover email issues procurement; email does not own the state machine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.database.procurement_request import ProcurementRequest
from app.database.project import Project
from app.email.models import ProjectEmailDraft
from app.email.providers.fake import FakeProvider
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
REQUEST_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
ARTEFACT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
EMAIL_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
SOURCE_ID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)
WORKSPACE_PATH = "04-projects/kavanagh-residence/06-procurement/electrical_rfq.md"
ISSUE_MESSAGE_ID = "sent-draft-1"


def _project(*, project_id: uuid.UUID = PROJECT_ID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=USER_ID,
        slug="kavanagh-residence",
        title="Kavanagh Residence",
        workspace_path="04-projects/kavanagh-residence",
        phase="procurement",
        status="active",
        project_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def _request(**overrides) -> ProcurementRequest:
    values = {
        "id": REQUEST_ID,
        "project_id": PROJECT_ID,
        "created_by_user_id": USER_ID,
        "kind": "trade_rfq",
        "target_name": "Electrical Services",
        "target_slug": "electrical_services",
        "status": "draft",
        "current_draft_artifact_id": ARTEFACT_ID,
        "issued_at": None,
        "closed_at": None,
        "revision": 2,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return ProcurementRequest(**values)


def _artefact() -> SimpleNamespace:
    return SimpleNamespace(
        id=ARTEFACT_ID,
        project_id=PROJECT_ID,
        workflow_type="trade_rfq_electrical_services",
        workspace_path=WORKSPACE_PATH,
        title="Electrical RFQ",
    )


class _QueryResult:
    def __init__(self, rows: list) -> None:
        self._rows = list(rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self._rows


class _LoopSession:
    def __init__(
        self,
        *,
        project: Project,
        request: ProcurementRequest | None = None,
        artefact=None,
        email_draft: ProjectEmailDraft | None = None,
        documents: dict | None = None,
        emails: dict | None = None,
        attachments: list | None = None,
        submissions: list | None = None,
        issued_requests: list | None = None,
    ) -> None:
        self.project = project
        self.request = request
        self.artefact = artefact
        self.email_draft = email_draft
        self.documents = documents or {}
        self.emails = emails or {}
        self.attachments = attachments or []
        self.submissions = submissions or []
        self.issued_requests = issued_requests or []
        self.added: list[object] = []
        self.commits = 0

    async def get(self, model, ident, with_for_update: bool = False):
        from app.database.draft_artifact import DraftArtifact
        from app.database.source_document import SourceDocument
        from app.email.models import ProjectEmail

        _ = with_for_update
        if model is Project and ident == self.project.id:
            return self.project
        if model is ProcurementRequest and self.request is not None and ident == self.request.id:
            return self.request
        if model is DraftArtifact and self.artefact is not None and ident == self.artefact.id:
            return self.artefact
        if model is ProjectEmailDraft and self.email_draft is not None and ident == self.email_draft.id:
            return self.email_draft
        if model is SourceDocument:
            return self.documents.get(ident)
        if model is ProjectEmail:
            return self.emails.get(ident)
        return None

    def add(self, obj) -> None:
        self.added.append(obj)
        if isinstance(obj, ProjectEmailDraft):
            self.email_draft = obj
        if obj.__class__.__name__ == "ProcurementRequestSubmission":
            self.submissions.append(obj)

    async def flush(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def execute(self, statement):
        from sqlalchemy.sql import Select

        from app.email.models import ProjectEmailAttachment

        if not isinstance(statement, Select):
            return _QueryResult([])
        entity = None
        if statement.column_descriptions:
            entity = statement.column_descriptions[0].get("entity")
        name = getattr(entity, "__name__", None)
        sql = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
        if entity is ProcurementRequest:
            if "'issued'" in sql:
                rows = [
                    row
                    for row in ([self.request] if self.request else [])
                    + self.issued_requests
                    if row is not None and row.status == "issued"
                ]
                return _QueryResult(rows)
            return _QueryResult([self.request] if self.request is not None else [])
        if entity is ProjectEmailAttachment:
            matches = [
                attachment
                for attachment in self.attachments
                if attachment.source_document_id is not None
                and str(attachment.source_document_id) in sql
            ]
            return _QueryResult(matches)
        if name == "ProcurementRequestSubmission":
            return _QueryResult(self.submissions)
        return _QueryResult([])


def test_draft_issue_email_leaves_request_in_draft() -> None:
    from app.procurement.issue import draft_procurement_issue_email

    provider = FakeProvider()
    request = _request()
    session = _LoopSession(
        project=_project(),
        request=request,
        artefact=_artefact(),
    )
    draft = run_async(
        draft_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            actor_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            provider=provider,
        )
    )
    assert request.status == "draft"
    assert request.revision == 2
    assert draft.status == "draft"
    assert provider.sent == []
    assert WORKSPACE_PATH in draft.body_text
    assert "Electrical Services" in draft.subject
    assert request.issue_email_draft_id == draft.id


def test_draft_issue_email_without_artefact_raises() -> None:
    from app.procurement.issue import draft_procurement_issue_email
    from app.procurement.requests import ProcurementRequestDraftConflict

    session = _LoopSession(
        project=_project(),
        request=_request(current_draft_artifact_id=None),
    )
    with pytest.raises(ProcurementRequestDraftConflict):
        run_async(
            draft_procurement_issue_email(
                session,
                project_id=PROJECT_ID,
                request_id=REQUEST_ID,
                actor_id=USER_ID,
                to_addresses=["qs@consultant.com"],
            )
        )
    assert session.request is not None
    assert session.request.status == "draft"


def test_send_issue_email_sets_status_issued() -> None:
    from app.procurement.issue import (
        draft_procurement_issue_email,
        send_procurement_issue_email,
    )

    provider = FakeProvider()
    request = _request()
    session = _LoopSession(
        project=_project(),
        request=request,
        artefact=_artefact(),
    )
    draft = run_async(
        draft_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            actor_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            provider=provider,
        )
    )
    issued = run_async(
        send_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            draft_id=draft.id,
            actor_id=USER_ID,
            expected_revision=2,
            provider=provider,
        )
    )
    assert issued.status == "issued"
    assert issued.issued_at is not None
    assert draft.status == "sent"
    assert len(provider.sent) == 1


def test_send_failure_leaves_request_draft() -> None:
    from app.procurement.issue import (
        draft_procurement_issue_email,
        send_procurement_issue_email,
    )

    class _BoomProvider(FakeProvider):
        async def send_draft(
            self,
            provider_draft_id: str,
            *,
            actor_id: uuid.UUID | None,
            draft=None,
        ):
            raise RuntimeError("mailbox unavailable")

    provider = _BoomProvider()
    request = _request()
    session = _LoopSession(
        project=_project(),
        request=request,
        artefact=_artefact(),
    )
    draft = run_async(
        draft_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            actor_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            provider=provider,
        )
    )
    with pytest.raises(RuntimeError, match="mailbox unavailable"):
        run_async(
            send_procurement_issue_email(
                session,
                project_id=PROJECT_ID,
                request_id=REQUEST_ID,
                draft_id=draft.id,
                actor_id=USER_ID,
                expected_revision=2,
                provider=provider,
            )
        )
    assert request.status == "draft"
    assert draft.status == "send_failed"


def test_retry_after_transition_failure_does_not_send_a_second_email() -> None:
    from unittest.mock import patch

    from app.procurement.issue import (
        draft_procurement_issue_email,
        send_procurement_issue_email,
    )

    provider = FakeProvider()
    request = _request()
    session = _LoopSession(
        project=_project(),
        request=request,
        artefact=_artefact(),
    )
    draft = run_async(
        draft_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            actor_id=USER_ID,
            to_addresses=["qs@consultant.com"],
            provider=provider,
        )
    )

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("transition failed")

    with patch("app.procurement.issue.transition_procurement_request", new=_boom):
        with pytest.raises(RuntimeError, match="transition failed"):
            run_async(
                send_procurement_issue_email(
                    session,
                    project_id=PROJECT_ID,
                    request_id=REQUEST_ID,
                    draft_id=draft.id,
                    actor_id=USER_ID,
                    expected_revision=2,
                    provider=provider,
                )
            )
    assert request.status == "draft"
    assert draft.status == "sent"
    assert len(provider.sent) == 1

    issued = run_async(
        send_procurement_issue_email(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            draft_id=draft.id,
            actor_id=USER_ID,
            expected_revision=2,
            provider=provider,
        )
    )
    assert issued.status == "issued"
    assert len(provider.sent) == 1


def test_send_issue_on_another_project_returns_404() -> None:
    from unittest.mock import patch

    from app.auth.dependencies import CurrentUser, get_current_user
    from app.database.session import get_db
    from app.main import fastapi_app as app
    from app.procurement.requests import ProcurementRequestNotFound

    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield _LoopSession(project=_project())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=_project()),
        ),
        patch(
            "app.api.projects.require_active_entitlement",
            new=AsyncMock(),
        ),
        patch(
            "app.api.projects.get_procurement_request",
            new=AsyncMock(side_effect=ProcurementRequestNotFound(str(REQUEST_ID))),
        ),
        TestClient(app) as client,
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/procurement-requests/{REQUEST_ID}/issue-email/send",
            json={
                "draft_id": str(uuid.uuid4()),
                "expected_revision": 2,
            },
        )
    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.status_code != 403


def _source_document(**overrides):
    from app.database.source_document import SourceDocument

    fields = {
        "id": SOURCE_ID,
        "project_id": PROJECT_ID,
        "project": "kavanagh-residence",
        "phase": "procurement",
        "document_class": "commercial",
        "filename": "electrical_services_quote.pdf",
        "relative_path": "04-projects/kavanagh-residence/_inbox/electrical_services_quote.pdf",
        "normalized_content": "quote",
        "document_metadata": {"procurement_stage": "submission", "source": "email"},
    }
    fields.update(overrides)
    return SourceDocument(**fields)


def _reply_email(**overrides):
    from app.email.models import ProjectEmail

    fields = {
        "id": EMAIL_ID,
        "provider": "fake",
        "provider_message_id": "reply-1",
        "provider_thread_id": "thread-1",
        "internet_message_id": "<reply-1@example.com>",
        "from_address": "qs@consultant.com",
        "to_addresses": ["pm@owner.com"],
        "cc_addresses": [],
        "subject": "Re: Request for Quotation: Electrical Services",
        "sent_at": NOW,
        "body_text": "Please find our quotation attached.",
        "headers": {"in-reply-to": ISSUE_MESSAGE_ID},
        "content_hash": "b" * 64,
        "created_at": NOW,
    }
    fields.update(overrides)
    return ProjectEmail(**fields)


def _attachment(*, email_id: uuid.UUID = EMAIL_ID, source_id: uuid.UUID = SOURCE_ID):
    from app.email.models import ProjectEmailAttachment

    return ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=email_id,
        provider_attachment_id="att-1",
        filename="electrical_services_quote.pdf",
        content_type="application/pdf",
        size_bytes=12,
        source_document_id=source_id,
    )


def _sent_issue_draft() -> ProjectEmailDraft:
    return ProjectEmailDraft(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        created_by_user_id=USER_ID,
        to_addresses=["qs@consultant.com", "estimator@contractor.com"],
        cc_addresses=[],
        subject="Request for Quotation: Electrical Services",
        body_text=WORKSPACE_PATH,
        status="sent",
        provider_message_id=ISSUE_MESSAGE_ID,
        references={"kind": "procurement_issue", "procurement_request_id": str(REQUEST_ID)},
    )


def test_reply_attachment_classified_submission_links_to_issued_request() -> None:
    from app.procurement.submissions import link_submission_to_request

    draft = _sent_issue_draft()
    request = _request(
        status="issued",
        issue_email_draft_id=draft.id,
        issued_at=NOW,
    )
    document = _source_document()
    email = _reply_email()
    session = _LoopSession(
        project=_project(),
        request=request,
        email_draft=draft,
        documents={document.id: document},
        emails={email.id: email},
        attachments=[_attachment()],
        issued_requests=[request],
    )
    linked = run_async(
        link_submission_to_request(
            session, project_id=PROJECT_ID, source_document_id=document.id
        )
    )
    assert linked is not None
    assert linked.id == request.id
    assert len(session.submissions) == 1
    assert session.submissions[0].source_document_id == document.id
    assert session.submissions[0].request_id == request.id


def test_unrelated_quote_does_not_link() -> None:
    from app.procurement.submissions import link_submission_to_request

    draft = _sent_issue_draft()
    request = _request(
        status="issued",
        issue_email_draft_id=draft.id,
        issued_at=NOW,
    )
    document = _source_document(
        filename="plumbing_quote.pdf",
        relative_path="04-projects/kavanagh-residence/_inbox/plumbing_quote.pdf",
    )
    email = _reply_email(
        provider_message_id="other-1",
        provider_thread_id="other-thread",
        subject="Plumbing quotation",
        headers={},
        from_address="plumber@example.com",
    )
    session = _LoopSession(
        project=_project(),
        request=request,
        email_draft=draft,
        documents={document.id: document},
        emails={email.id: email},
        attachments=[
            _attachment(email_id=email.id, source_id=document.id)
        ],
        issued_requests=[request],
    )
    linked = run_async(
        link_submission_to_request(
            session, project_id=PROJECT_ID, source_document_id=document.id
        )
    )
    assert linked is None
    assert session.submissions == []


def test_email_module_does_not_write_procurement_stage() -> None:
    from pathlib import Path

    hits: list[str] = []
    email_root = Path(__file__).resolve().parents[2] / "app" / "email"
    for path in email_root.rglob("*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "procurement_stage" in line:
                hits.append(f"{path.relative_to(email_root.parent.parent)}:{line_no}:{line.strip()}")
    assert hits == []


def test_chase_missing_bidders_creates_draft_without_sending() -> None:
    from app.database.procurement_request_submission import (
        ProcurementRequestSubmission,
    )
    from app.procurement.issue import draft_chase_missing_bidders

    provider = FakeProvider()
    issue_draft = _sent_issue_draft()
    request = _request(
        status="issued",
        issue_email_draft_id=issue_draft.id,
        issued_at=NOW,
    )
    session = _LoopSession(
        project=_project(),
        request=request,
        email_draft=issue_draft,
        submissions=[
            ProcurementRequestSubmission(
                request_id=request.id,
                source_document_id=SOURCE_ID,
            )
        ],
    )
    chase = run_async(
        draft_chase_missing_bidders(
            session,
            project_id=PROJECT_ID,
            request_id=REQUEST_ID,
            actor_id=USER_ID,
            provider=provider,
        )
    )
    assert chase.status == "draft"
    assert chase.id != issue_draft.id
    assert provider.sent == []
    assert request.status == "issued"
    assert "Electrical Services" in chase.subject


def test_link_submission_does_not_import_tender() -> None:
    import ast
    from pathlib import Path

    roots = [
        Path(__file__).resolve().parents[2] / "app" / "email",
        Path(__file__).resolve().parents[2] / "app" / "procurement",
    ]
    imports: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "tender" or alias.name.startswith("tender."):
                            imports.append(f"{path}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module == "tender" or node.module.startswith("tender."):
                        imports.append(f"{path}: from {node.module}")
    assert imports == []


def test_commercial_submission_filter_includes_email_ingested_files() -> None:
    from sqlalchemy import select

    from app.database.source_document import SourceDocument
    from app.retrieval.queries import apply_document_filters
    from app.retrieval.schemas import RetrievalFilters

    filters = RetrievalFilters(
        document_class="commercial", procurement_stage="submission"
    )
    stmt = apply_document_filters(select(SourceDocument.id), filters)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "commercial" in sql
    assert "submission" in sql
    assert "email" not in sql.lower()
    assert "source_type" not in sql.lower()

