"""Human classification override. REST and MCP both call this (D4, D8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import get_args, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database.document_classification_override import DocumentClassificationOverride
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.consultant_facts import upsert_consultant_fact_from_document
from app.projects.event_spine import record_project_verb, verb_dedup_key
from app.projects.events import publish_project_event
from ingest.categories import canonical_category
from ingest.types import Classification, DocumentClass, DocumentSubject, IngestMode

_USER_CONFIDENCE = "1.0"


class DocumentClassificationNotFound(LookupError):
    pass


class DocumentClassificationInvalid(ValueError):
    pass


def classification_from_override(
    row: object, *, machine: Classification | None = None
) -> Classification:
    """Replace interpretation; preserve every observed metadata key (OD-5)."""
    document_class = cast(DocumentClass, getattr(row, "document_class"))
    raw_subject = getattr(row, "document_subject", None) or "none"
    subject = canonical_category(raw_subject)
    metadata: dict[str, str] = {}
    ingest_mode: IngestMode = "full_text"
    if machine is not None:
        metadata.update(machine.document_metadata)
        ingest_mode = machine.ingest_mode
        metadata.setdefault("machine_class", machine.document_class)
        metadata.setdefault("machine_subject", machine.document_subject)
        metadata.setdefault(
            "machine_confidence", f"{machine.confidence:.2f}"
        )
        metadata.setdefault("machine_basis", machine.basis)
    metadata["basis"] = "user"
    metadata["confidence"] = _USER_CONFIDENCE
    metadata["subject"] = subject
    return Classification(
        document_class=document_class,
        document_subject=subject,
        ingest_mode=ingest_mode,
        document_metadata=metadata,
        confidence=1.0,
        basis="user",
    )


def _hash_lookup(project_id: uuid.UUID, content_hash: str):
    return select(DocumentClassificationOverride).where(
        DocumentClassificationOverride.project_id == project_id,
        DocumentClassificationOverride.content_hash == content_hash,
    )


def _path_lookup(project_id: uuid.UUID, relative_path: str):
    return select(DocumentClassificationOverride).where(
        DocumentClassificationOverride.project_id == project_id,
        DocumentClassificationOverride.relative_path == relative_path,
        DocumentClassificationOverride.key_basis == "relative_path",
    )


async def lookup_override(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    content_hash: str | None,
    relative_path: str,
) -> DocumentClassificationOverride | None:
    if content_hash:
        result = await session.execute(_hash_lookup(project_id, content_hash))
        row = result.scalar_one_or_none()
        if row is not None:
            return row
    result = await session.execute(_path_lookup(project_id, relative_path))
    return result.scalar_one_or_none()


def lookup_override_sync(
    session,
    *,
    project_id: uuid.UUID,
    content_hash: str | None,
    relative_path: str,
) -> DocumentClassificationOverride | None:
    if content_hash:
        row = session.scalar(_hash_lookup(project_id, content_hash))
        if row is not None:
            return row
    return session.scalar(_path_lookup(project_id, relative_path))


def _validate_vocab(
    document_class: DocumentClass,
    document_subject: DocumentSubject | None,
) -> DocumentSubject:
    if document_class not in get_args(DocumentClass):
        raise DocumentClassificationInvalid(
            f"document_class is not canonical: {document_class}"
        )
    subject = canonical_category(document_subject)
    if (
        subject == "none"
        and document_subject
        and str(document_subject).strip().lower() not in {"none", "unassigned"}
    ):
        raise DocumentClassificationInvalid(
            f"document_subject is not canonical: {document_subject}"
        )
    return subject


async def set_document_classification(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_class: DocumentClass,
    document_subject: DocumentSubject | None,
    actor_id: uuid.UUID,
    reason: str | None = None,
) -> SourceDocument:
    """Record a human override and apply it. basis=user, confidence=1.0 (D4)."""
    subject = _validate_vocab(document_class, document_subject)
    document = await session.get(SourceDocument, document_id)
    if document is None or document.project_id != project_id:
        raise DocumentClassificationNotFound(str(document_id))

    previous_class = document.document_class
    if document.content_hash:
        key_basis = "content_hash"
        content_hash = document.content_hash
        relative_path = document.relative_path
    else:
        key_basis = "relative_path"
        content_hash = None
        relative_path = document.relative_path

    existing = await lookup_override(
        session,
        project_id=project_id,
        content_hash=content_hash,
        relative_path=relative_path,
    )
    now = datetime.now(UTC)
    if existing is None:
        existing = DocumentClassificationOverride(
            id=uuid.uuid4(),
            project_id=project_id,
            content_hash=content_hash,
            relative_path=relative_path,
            key_basis=key_basis,
            document_class=document_class,
            document_subject=subject,
            previous_class=previous_class,
            reason=reason,
            actor_id=actor_id,
        )
        session.add(existing)
    else:
        existing.document_class = document_class
        existing.document_subject = subject
        existing.previous_class = previous_class
        existing.reason = reason
        existing.actor_id = actor_id
        existing.updated_at = now
        if key_basis == "content_hash":
            existing.content_hash = content_hash
            existing.relative_path = relative_path
            existing.key_basis = key_basis

    document.document_class = document_class
    document.ingest_mode = "full_text"
    metadata = dict(document.document_metadata or {})
    metadata["basis"] = "user"
    metadata["confidence"] = _USER_CONFIDENCE
    metadata["subject"] = subject
    document.document_metadata = metadata
    flag_modified(document, "document_metadata")

    project = await session.get(Project, project_id)
    if project is not None:
        upsert_consultant_fact_from_document(project, document)

    await publish_project_event(
        session,
        project_id=project_id,
        actor_source="user",
        resource_type="source_document",
        resource_id=document.id,
        resource_revision=None,
        action="classification_override",
        payload={
            "document_class": document_class,
            "document_subject": subject,
            "previous_class": previous_class,
            "key_basis": key_basis,
        },
        changes_context=False,
        locked_project=project,
    )
    await record_project_verb(
        session,
        project_id=project_id,
        verb="document.reclassified",
        reference_type="source_document",
        reference_id=document.id,
        message=(
            f"Reclassified {document.filename} from {previous_class} to {document_class}"
        ),
        deduplication_key=verb_dedup_key(
            "document.reclassified",
            reference_type="source_document",
            reference_id=document.id,
            extra=f"{previous_class}:{document_class}:{document.content_hash or ''}",
        ),
        metadata={
            "filename": document.filename,
            "document_class": document_class,
            "document_subject": subject,
            "content_hash": document.content_hash,
        },
    )
    await session.flush()
    return document
