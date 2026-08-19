"""X1 Stage 16: email attachments enter canonical intake through inbox upload."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.inbox.service import InboxUploadItem, InboxUploadOutcome
from ingest.hashing import bytes_content_hash
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SOURCE_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
WORKSPACE_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
NOW = datetime(2026, 8, 19, 11, 0, tzinfo=UTC)


def _project(project_id: uuid.UUID, *, slug: str) -> Project:
    return Project(
        id=project_id,
        owner_user_id=USER_ID,
        slug=slug,
        title=slug,
        workspace_path=f"04-projects/{slug}",
        phase="procurement",
        status="active",
        project_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def _outcome(*, content: bytes, filename: str) -> InboxUploadOutcome:
    return InboxUploadOutcome(
        id=WORKSPACE_ID,
        filename=filename,
        workspace_path=f"04-projects/demo/_inbox/{filename}",
        content_hash=bytes_content_hash(content),
        size_bytes=len(content),
        ingest_status="queued",
        message="Uploaded; ingestion queued",
        workflow_run_id=uuid.uuid4(),
    )


class _IntakeSession:
    def __init__(
        self,
        *,
        interpretation=None,
        attachment=None,
        workspace=None,
    ) -> None:
        self.interpretation = interpretation
        self.attachment = attachment
        self.workspace = workspace
        self.commit = AsyncMock()

    async def get(self, model, ident):
        from app.database.workspace_file import WorkspaceFile
        from app.email.models import ProjectEmailInterpretation

        if model is ProjectEmailInterpretation and self.interpretation is not None:
            return self.interpretation if ident == self.interpretation.email_id else None
        if model is WorkspaceFile and self.workspace is not None:
            return self.workspace if ident == self.workspace.id else None
        return None

    async def execute(self, statement):
        _ = statement
        return SimpleNamespace(scalar_one_or_none=lambda: self.attachment)


def test_ingest_email_attachment_calls_inbox_upload_not_classify_entry() -> None:
    from app.email.attachments import ingest_email_attachment
    from app.email.models import ProjectEmailAttachment, ProjectEmailInterpretation

    content = b"%PDF-1.4 invoice bytes"
    filename = "invoice.pdf"
    interpretation = ProjectEmailInterpretation(
        email_id=EMAIL_ID,
        project_id=PROJECT_A,
        match_basis="user",
        updated_at=NOW,
    )
    attachment = ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=EMAIL_ID,
        provider_attachment_id="att-1",
        filename=filename,
        content_type="application/pdf",
        size_bytes=len(content),
        content_hash=None,
        source_document_id=None,
    )
    workspace = SimpleNamespace(id=WORKSPACE_ID, source_document_id=SOURCE_ID)
    session = _IntakeSession(
        interpretation=interpretation,
        attachment=attachment,
        workspace=workspace,
    )
    captured: list[InboxUploadItem] = []

    async def _store(session, *, project, item, user_id, snapshot):
        _ = session, project, user_id, snapshot
        captured.append(item)
        return _outcome(content=item.content, filename=item.filename)

    with (
        patch("app.email.attachments.store_and_queue_inbox_file", new=_store),
        patch(
            "app.email.attachments.get_project_snapshot",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch("ingest.classify.classify_entry") as classify,
        patch("app.cost_plan.invoice_extraction.extract_invoice") as extract,
    ):
        outcome = run_async(
            ingest_email_attachment(
                session,
                project=_project(PROJECT_A, slug="alpha"),
                email_id=EMAIL_ID,
                filename=filename,
                content=content,
                created_by_user_id=USER_ID,
            )
        )

    assert len(captured) == 1
    assert captured[0].content == content
    assert captured[0].filename == filename
    assert captured[0].ingest_metadata == {
        "source": "email",
        "email_id": str(EMAIL_ID),
    }
    classify.assert_not_called()
    extract.assert_not_called()
    assert outcome.content_hash == bytes_content_hash(content)
    assert attachment.content_hash == bytes_content_hash(content)
    assert attachment.source_document_id == SOURCE_ID
    import app.email.attachments as attachments_mod

    assert not hasattr(attachments_mod, "classify_entry")
    assert "extract_invoice" not in Path(attachments_mod.__file__).read_text(
        encoding="utf-8"
    )


def test_attachment_hash_matches_bytes_content_hash() -> None:
    from app.email.attachments import ingest_email_attachment
    from app.email.models import ProjectEmailAttachment, ProjectEmailInterpretation

    content = b"TAX INVOICE\nInvoice No 0043\n"
    filename = "Invoice 0043.md"
    attachment = ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=EMAIL_ID,
        provider_attachment_id="att-hash",
        filename=filename,
        content_type="text/markdown",
        size_bytes=len(content),
        content_hash=None,
        source_document_id=None,
    )
    session = _IntakeSession(
        interpretation=ProjectEmailInterpretation(
            email_id=EMAIL_ID,
            project_id=PROJECT_A,
            match_basis="alias",
            updated_at=NOW,
        ),
        attachment=attachment,
        workspace=SimpleNamespace(id=WORKSPACE_ID, source_document_id=None),
    )

    async def _store(session, *, project, item, user_id, snapshot):
        _ = session, project, user_id, snapshot
        return _outcome(content=item.content, filename=item.filename)

    with (
        patch("app.email.attachments.store_and_queue_inbox_file", new=_store),
        patch(
            "app.email.attachments.get_project_snapshot",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
    ):
        outcome = run_async(
            ingest_email_attachment(
                session,
                project=_project(PROJECT_A, slug="alpha"),
                email_id=EMAIL_ID,
                filename=filename,
                content=content,
                created_by_user_id=USER_ID,
            )
        )

    assert outcome.content_hash == bytes_content_hash(content)
    assert attachment.content_hash == bytes_content_hash(content)


def test_unmatched_email_attachment_is_not_ingested() -> None:
    from app.email.attachments import (
        EmailAttachmentUnmatched,
        ingest_email_attachment,
    )
    from app.email.models import ProjectEmailInterpretation

    session = _IntakeSession(
        interpretation=ProjectEmailInterpretation(
            email_id=EMAIL_ID,
            project_id=None,
            updated_at=NOW,
        )
    )
    store = AsyncMock()
    with patch("app.email.attachments.store_and_queue_inbox_file", new=store):
        with pytest.raises(EmailAttachmentUnmatched):
            run_async(
                ingest_email_attachment(
                    session,
                    project=_project(PROJECT_A, slug="alpha"),
                    email_id=EMAIL_ID,
                    filename="invoice.pdf",
                    content=b"%PDF-bytes",
                    created_by_user_id=USER_ID,
                )
            )
    store.assert_not_called()


def test_missing_interpretation_is_not_ingested() -> None:
    from app.email.attachments import (
        EmailAttachmentUnmatched,
        ingest_email_attachment,
    )

    store = AsyncMock()
    with patch("app.email.attachments.store_and_queue_inbox_file", new=store):
        with pytest.raises(EmailAttachmentUnmatched):
            run_async(
                ingest_email_attachment(
                    _IntakeSession(),
                    project=_project(PROJECT_A, slug="alpha"),
                    email_id=EMAIL_ID,
                    filename="invoice.pdf",
                    content=b"%PDF-bytes",
                    created_by_user_id=USER_ID,
                )
            )
    store.assert_not_called()


VOLATILE = {"extracted_at", "run_id", "source_document_id", "project_id"}
QUOIN = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "synthetic-mobilisation-evidence"
    / "kavanagh-residence-cost-files"
    / "11-tax-invoice-quoin-architecture-01.md"
)


def comparable(snapshot: dict) -> dict:
    """Drop run-local identifiers. Never drop invoice_number or money fields."""

    def _scrub(value):
        if isinstance(value, dict):
            return {
                key: _scrub(item)
                for key, item in value.items()
                if key not in VOLATILE and key != "source_path"
            }
        if isinstance(value, list):
            return [_scrub(item) for item in value]
        return value

    return _scrub(snapshot)


def _snapshot(project: Project):
    from app.schemas.project_snapshot import ProjectSnapshot

    return ProjectSnapshot.model_validate(
        {
            "schema_version": 1,
            "generated_at": "2026-08-19T00:00:00Z",
            "content_fingerprint": "a" * 64,
            "identity": {
                "project_id": project.id,
                "title": project.title,
                "slug": project.slug,
                "workspace_path": project.workspace_path,
                "phase": project.phase,
                "status": project.status,
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": project.id,
                "profile_revision": 1,
                "building_class": "class-1a",
                "work_type": "new",
                "subclasses": ["detached-house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 1, "items": []},
            "evidence": {
                "fingerprint": "b" * 64,
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


@contextmanager
def _inbox_runtime_patches(project: Project):
    with (
        patch(
            "app.inbox.service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch("app.inbox.service.upload_project_file", return_value="storage-key"),
        patch("app.inbox.service.lock_project", new=AsyncMock(return_value=project)),
        patch(
            "app.inbox.service.start_workflow_run",
            new=AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), True)),
        ),
        patch(
            "app.inbox.service.upsert_workspace_file",
            new=AsyncMock(
                side_effect=lambda session, **kwargs: SimpleNamespace(
                    id=uuid.uuid4(),
                    **{"source_document_id": uuid.uuid4(), **kwargs},
                )
            ),
        ),
        patch("app.inbox.service.record_project_verb", new=AsyncMock()),
        patch("app.inbox.service.record_activity_events", new=AsyncMock()),
    ):
        yield


def _book_invoice(project_id: uuid.UUID, content: bytes, filename: str, relative_path: str):
    from unittest.mock import MagicMock

    from app.cost_plan.invoice_candidates import InvoiceCandidate
    from app.cost_plan.invoice_extraction import extract_invoice
    from app.cost_plan.invoice_service import book_invoice
    from app.cost_plan.schemas import InvoiceAllocationInput

    candidate = InvoiceCandidate(
        source_document_id=uuid.uuid4(),
        workspace_file_id=uuid.uuid4(),
        filename=filename,
        relative_path=relative_path,
        content_hash=bytes_content_hash(content),
        content=content.decode("utf-8"),
    )
    extracted = extract_invoice(candidate)
    empty = MagicMock()
    empty.scalars.return_value.first.return_value = None
    session = AsyncMock()
    session.execute.return_value = empty
    session.add = MagicMock()
    session.flush = AsyncMock()
    with patch("app.cost_plan.invoice_service.record_project_verb", new=AsyncMock()):
        result = run_async(
            book_invoice(
                session,
                project_id=project_id,
                created_by_user_id=USER_ID,
                candidate=candidate,
                extracted=extracted,
                allocations=[
                    InvoiceAllocationInput(
                        line_number=1,
                        description=extracted.lines[0].description,
                        amount_ex_gst=extracted.subtotal_ex_gst,
                        gst_treatment="taxable",
                        cost_item_key="architect",
                        cost_item_label="Architect",
                        mapping_method="exact",
                        review_status="mapped",
                    )
                ],
            )
        )
    assert result.invoice is not None
    return extracted, result.invoice


def test_email_invoice_matches_manual_upload_downstream() -> None:
    from app.email.attachments import ingest_email_attachment
    from app.email.models import ProjectEmailAttachment, ProjectEmailInterpretation
    from app.inbox.service import (
        InboxUploadItem,
        store_and_queue_inbox_file,
        upload_inbox_files,
    )
    from ingest.classify import classify_entry
    from ingest.types import ManifestEntry

    content = QUOIN.read_bytes()
    filename = QUOIN.name
    project_a = _project(PROJECT_A, slug="alpha")
    project_b = _project(PROJECT_B, slug="bravo")
    captured: list[InboxUploadItem] = []
    original_store = store_and_queue_inbox_file

    async def capturing_store(session, *, project, item, user_id, snapshot):
        captured.append(item)
        return await original_store(
            session,
            project=project,
            item=item,
            user_id=user_id,
            snapshot=snapshot,
        )

    session_a = AsyncMock()
    session_a.commit = AsyncMock()
    with (
        patch("app.inbox.service.store_and_queue_inbox_file", new=capturing_store),
        _inbox_runtime_patches(project_a),
    ):
        outcomes_a = run_async(
            upload_inbox_files(
                session_a,
                project=project_a,
                items=[InboxUploadItem(filename=filename, content=content)],
                user_id=USER_ID,
                snapshot=_snapshot(project_a),
            )
        )

    email_id_b = uuid.uuid4()
    attachment_b = ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=email_id_b,
        provider_attachment_id="att-quoin",
        filename=filename,
        content_type="text/markdown",
        size_bytes=len(content),
        content_hash=None,
        source_document_id=None,
    )
    session_b = _IntakeSession(
        interpretation=ProjectEmailInterpretation(
            email_id=email_id_b,
            project_id=PROJECT_B,
            match_basis="user",
            updated_at=NOW,
        ),
        attachment=attachment_b,
        workspace=SimpleNamespace(id=WORKSPACE_ID, source_document_id=uuid.uuid4()),
    )
    with (
        patch("app.email.attachments.store_and_queue_inbox_file", new=capturing_store),
        patch(
            "app.email.attachments.get_project_snapshot",
            new=AsyncMock(return_value=_snapshot(project_b)),
        ),
        _inbox_runtime_patches(project_b),
    ):
        outcome_b = run_async(
            ingest_email_attachment(
                session_b,
                project=project_b,
                email_id=email_id_b,
                filename=filename,
                content=content,
                created_by_user_id=USER_ID,
            )
        )

    assert len(captured) == 2
    item_a, item_b = captured
    assert item_a.content == item_b.content == content
    assert item_a.filename == item_b.filename == filename
    assert item_b.ingest_metadata == {
        "source": "email",
        "email_id": str(email_id_b),
    }
    assert item_a.ingest_metadata in (None, {})
    assert (
        outcomes_a[0].content_hash
        == outcome_b.content_hash
        == bytes_content_hash(content)
    )

    def _classify(item: InboxUploadItem, slug: str):
        return classify_entry(
            ManifestEntry(
                absolute_path=Path(item.filename),
                relative_path=item.filename,
                project=slug,
                filename=item.filename,
                extension=".md",
                size_bytes=len(item.content),
            ),
            extracted_text=item.content.decode("utf-8"),
        )

    class_a = _classify(item_a, "alpha")
    class_b = _classify(item_b, "bravo")
    assert class_a.document_class == class_b.document_class
    assert class_a.document_metadata.get("commercial_type") == class_b.document_metadata.get(
        "commercial_type"
    )
    assert class_a.document_metadata.get("commercial_type") == "invoice"

    _extracted_a, invoice_a = _book_invoice(
        PROJECT_A, item_a.content, item_a.filename, outcomes_a[0].workspace_path
    )
    _extracted_b, invoice_b = _book_invoice(
        PROJECT_B, item_b.content, item_b.filename, outcome_b.workspace_path
    )
    snapshot_a = invoice_a.machine_extraction
    snapshot_b = invoice_b.machine_extraction
    assert comparable(snapshot_a) == comparable(snapshot_b)
    assert snapshot_a["subtotal_ex_gst"] == snapshot_b["subtotal_ex_gst"]
    assert snapshot_a["gst"] == snapshot_b["gst"]
    assert snapshot_a["total_including_gst"] == snapshot_b["total_including_gst"]
    assert snapshot_a["invoice_number"] == snapshot_b["invoice_number"]
    assert invoice_a.review_state == invoice_b.review_state
