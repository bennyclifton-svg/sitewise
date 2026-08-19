"""Closed project-verb vocabulary on activity_events.

Pulse (14) and email (15) read this log. They do not invent a second table.
Verbs reference canonical state; they do not copy it (D5).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal, get_args

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_event import ActivityEvent
from app.database.source_document import SourceDocument
from app.logging import get_logger

log = get_logger(__name__)  # patched in tests to prove duplicates do not log.error

ProjectVerb = Literal[
    "document.received",
    "document.extracted",
    "document.classified",
    "document.reclassified",
    "document.filed",
    "document.revised",
    "invoice.received",
    "invoice.needs_review",
    "invoice.approved",
    "invoice.rejected",
    "invoice.posted",
    "invoice.duplicate",
    "invoice.conflict",
    "email.received",
    "email.linked",
    "email.action_detected",
    "project_signal.detected",
    "project_signal.dismissed",
]

PROJECT_VERBS: frozenset[str] = frozenset(get_args(ProjectVerb))

_ALLOWED_METADATA = frozenset(
    {
        "filename",
        "document_class",
        "document_subject",
        "drawing_number",
        "revision",
        "previous_revision",
        "invoice_number",
        "signal_type",
        "subject_key",
        "confidence",
        "issue_codes",
        "content_hash",
    }
)
_MAX_MESSAGE = 500
_REV_PREFIX = re.compile(r"^(?:rev(?:ision)?\s+)", re.IGNORECASE)
_NUMERIC_REVISION = re.compile(r"^\d+$")


def verb_dedup_key(
    verb: str, *, reference_type: str, reference_id: uuid.UUID, extra: str = ""
) -> str:
    base = f"{verb}:{reference_type}:{reference_id}"
    return f"{base}:{extra}" if extra else base


def _filter_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key in _ALLOWED_METADATA}


def revision_sort_key(revision: str) -> tuple[int, int | str]:
    """Numeric-looking revisions compare as ints; letters case-insensitively.

    `Rev 10` > `Rev 9`. `C` > `B`. Prefixes `Rev` / `Revision` are stripped.
    """
    token = _REV_PREFIX.sub("", revision.strip())
    if _NUMERIC_REVISION.fullmatch(token):
        return (0, int(token))
    return (1, token.casefold())


async def record_project_verb(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    verb: ProjectVerb,
    reference_type: str,
    reference_id: uuid.UUID,
    message: str,
    deduplication_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> ActivityEvent | None:
    """Append one Pulse verb. No-op if the key already exists. Never copies
    canonical row state — metadata is an allow-list of display refs."""
    if verb not in PROJECT_VERBS:
        raise ValueError(f"unknown project verb: {verb}")

    event_id = uuid.uuid4()
    run_id = uuid.uuid4()
    safe_message = message[:_MAX_MESSAGE]
    safe_metadata = _filter_metadata(metadata)
    stmt = (
        pg_insert(ActivityEvent)
        .values(
            id=event_id,
            project_id=project_id,
            run_id=run_id,
            source=verb,
            reference_type=reference_type,
            reference_id=reference_id,
            step=verb,
            status="complete",
            message=safe_message,
            event_metadata=safe_metadata,
            deduplication_key=deduplication_key,
        )
        .on_conflict_do_nothing(
            index_elements=["project_id", "deduplication_key"],
            index_where=ActivityEvent.deduplication_key.isnot(None),
        )
        .returning(ActivityEvent.id)
    )
    inserted_id = (await session.execute(stmt)).scalar_one_or_none()
    if inserted_id is None:
        return None
    return ActivityEvent(
        id=inserted_id,
        project_id=project_id,
        run_id=run_id,
        source=verb,
        reference_type=reference_type,
        reference_id=reference_id,
        step=verb,
        status="complete",
        message=safe_message,
        event_metadata=safe_metadata,
        deduplication_key=deduplication_key,
    )


async def maybe_record_document_revised(
    session: AsyncSession,
    *,
    document: SourceDocument,
) -> ActivityEvent | None:
    """Emit document.revised when this drawing's revision advances the set."""
    if document.document_class != "drawing" or document.project_id is None:
        return None
    metadata = document.document_metadata or {}
    drawing_number = metadata.get("drawing_number")
    revision = metadata.get("revision")
    if not isinstance(drawing_number, str) or not drawing_number.strip():
        return None
    if not isinstance(revision, str) or not revision.strip():
        return None
    drawing_number = drawing_number.strip()
    revision = revision.strip()

    existing_result = await session.execute(
        select(SourceDocument.document_metadata).where(
            SourceDocument.project_id == document.project_id,
            SourceDocument.document_class == "drawing",
            SourceDocument.document_metadata["drawing_number"].astext == drawing_number,
            SourceDocument.id != document.id,
        )
    )
    existing_revisions = []
    for row in existing_result.all():
        payload = row.document_metadata if hasattr(row, "document_metadata") else row[0]
        if not isinstance(payload, dict):
            continue
        previous = payload.get("revision")
        if isinstance(previous, str) and previous.strip():
            existing_revisions.append(previous.strip())
    if not existing_revisions:
        return None
    previous_revision = max(existing_revisions, key=revision_sort_key)
    if revision_sort_key(revision) <= revision_sort_key(previous_revision):
        return None
    return await record_project_verb(
        session,
        project_id=document.project_id,
        verb="document.revised",
        reference_type="source_document",
        reference_id=document.id,
        message=(
            f"{drawing_number} Rev {revision} supersedes Rev {previous_revision}"
        ),
        deduplication_key=verb_dedup_key(
            "document.revised",
            reference_type="source_document",
            reference_id=document.id,
            extra=f"{drawing_number}:{revision}",
        ),
        metadata={
            "drawing_number": drawing_number,
            "revision": revision,
            "previous_revision": previous_revision,
            "filename": document.filename,
        },
    )


async def list_project_verbs(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    since: datetime | None = None,
    verbs: Sequence[str] | None = None,
    limit: int = 200,
) -> list[ActivityEvent]:
    wanted = PROJECT_VERBS if verbs is None else PROJECT_VERBS.intersection(verbs)
    stmt = (
        select(ActivityEvent)
        .where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.source.in_(wanted),
        )
        .order_by(ActivityEvent.created_at.desc())
        .limit(limit)
    )
    if since is not None:
        stmt = stmt.where(ActivityEvent.created_at > since)
    result = await session.execute(stmt)
    return list(result.scalars().all())
