"""Persist raw email separately from interpretation. Matching lives here (D4/D5)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm.attributes import flag_modified

from app.database.project import Project
from app.database.projects import list_projects
from app.email.attachments import ingest_email_attachment
from app.email.intelligence import (
    EmailActionCandidate,
    classify_message_category,
    detect_action_candidates,
)
from app.email.models import (
    RAW_EMAIL_COLUMNS,
    ProjectEmail,
    ProjectEmailAttachment,
    ProjectEmailDraft,
    ProjectEmailInterpretation,
    RawEmailImmutable,
)
from app.email.project_matching import (
    MATCH_REVIEW_CONFIDENCE_MIN,
    ProjectMatch,
    ProjectMatchCandidate,
    match_project,
)
from app.email.providers.base import EmailProvider
from app.email.schemas import ProviderDraft, RawProviderMessage
from app.projects.event_spine import record_project_verb, verb_dedup_key
from app.projects.project_knowledge import list_shared_project_objects
from ingest.hashing import bytes_content_hash


class EmailNotFound(LookupError):
    """Email is missing or is not linkable on this project (404, never 403)."""


class EmailDraftConflict(RuntimeError):
    """Draft is not in a state that can be sent (409)."""


def email_content_hash(
    *,
    internet_message_id: str | None,
    from_address: str,
    sent_at: datetime | None,
    subject: str,
    body_text: str,
) -> str:
    """Canonical hash so two providers delivering one message agree."""
    sent = sent_at.isoformat() if sent_at is not None else ""
    canonical = "\n".join(
        [
            internet_message_id or "",
            from_address,
            sent,
            subject,
            body_text,
        ]
    )
    return bytes_content_hash(canonical.encode("utf-8"))


def should_ingest_attachments(match: ProjectMatch) -> bool:
    if match.project_id is None:
        return False
    if match.basis == "user":
        return True
    return match.confidence >= MATCH_REVIEW_CONFIDENCE_MIN


async def update_email_interpretation(
    session: AsyncSession,
    email_id: uuid.UUID,
    **fields: Any,
) -> ProjectEmailInterpretation:
    """Update derived match/summary. Raw columns are refused."""
    raw_hits = RAW_EMAIL_COLUMNS.intersection(fields)
    if raw_hits:
        raise RawEmailImmutable(
            "refusing raw project_emails update: " + ", ".join(sorted(raw_hits))
        )
    email = await session.get(ProjectEmail, email_id)
    if email is None:
        raise KeyError(email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is None:
        interpretation = ProjectEmailInterpretation(
            email_id=email_id,
            updated_at=datetime.now(UTC),
        )
        session.add(interpretation)
    for key, value in fields.items():
        setattr(interpretation, key, value)
    interpretation.updated_at = datetime.now(UTC)
    return interpretation


async def link_email_to_project(
    session: AsyncSession,
    *,
    email_id: uuid.UUID,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: str | None,
    provider: EmailProvider | None = None,
) -> ProjectEmailInterpretation:
    """User link sets basis=user at confidence 1.0. Does not UPDATE raw columns."""
    _ = reason
    email = await session.get(ProjectEmail, email_id)
    if email is None:
        raise EmailNotFound(email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is not None and interpretation.project_id not in (
        None,
        project_id,
    ):
        raise EmailNotFound(email_id)
    updated = await update_email_interpretation(
        session,
        email_id,
        project_id=project_id,
        match_confidence=Decimal("1.000"),
        match_basis="user",
        match_reviewed_by_user_id=actor_id,
    )
    await _persist_intelligence(session, email=email, interpretation=updated)
    await _emit_email_project_verbs(
        session, email=email, project_id=project_id, interpretation=updated
    )
    await _maybe_ingest_matched_attachments(
        session,
        email=email,
        interpretation=updated,
        actor_id=actor_id,
        provider=provider,
    )
    return updated


async def rematch_email(
    session: AsyncSession,
    *,
    email_id: uuid.UUID,
    candidates: Sequence[ProjectMatchCandidate],
    prior_thread_project_id: uuid.UUID | None,
    actor_id: uuid.UUID | None = None,
    provider: EmailProvider | None = None,
) -> ProjectEmailInterpretation:
    """Re-score a message. Refuses to downgrade basis=user."""
    email = await session.get(ProjectEmail, email_id)
    if email is None:
        raise EmailNotFound(email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is not None and interpretation.match_basis == "user":
        return interpretation
    match = match_project(
        email=email,
        candidates=candidates,
        prior_thread_project_id=prior_thread_project_id,
        user_override=None,
    )
    updated = await update_email_interpretation(
        session,
        email_id,
        project_id=match.project_id,
        match_confidence=Decimal(str(round(match.confidence, 3))),
        match_basis=match.basis,
    )
    await _persist_intelligence(session, email=email, interpretation=updated)
    if match.project_id is not None:
        await _emit_email_project_verbs(
            session,
            email=email,
            project_id=match.project_id,
            interpretation=updated,
        )
    await _maybe_ingest_matched_attachments(
        session,
        email=email,
        interpretation=updated,
        actor_id=actor_id,
        provider=provider,
    )
    return updated


async def load_project_match_candidates(
    session: AsyncSession, owner_user_id: uuid.UUID
) -> list[ProjectMatchCandidate]:
    projects = await list_projects(session, owner_user_id)
    return [_candidate_from_project(project) for project in projects]


async def import_provider_messages(
    session: AsyncSession,
    *,
    provider: EmailProvider,
    actor_id: uuid.UUID | None,
) -> int:
    """Insert raw rows. Interpretation is inserted only when none exists."""
    messages: list[RawProviderMessage] = await provider.list_messages(since=None)
    candidates: list[ProjectMatchCandidate] = []
    if actor_id is not None:
        candidates = await load_project_match_candidates(session, actor_id)
    inserted = 0
    for message in messages:
        email_id = await _insert_raw_email(session, message)
        is_new = email_id is not None
        if email_id is None:
            email_id = await _existing_email_id(session, message)
        else:
            inserted += 1
        await _insert_attachment_refs(session, email_id, message)
        match = ProjectMatch(project_id=None, confidence=0.0, basis="default")
        email = _email_from_message(message, email_id)
        if is_new and actor_id is not None:
            prior = await lookup_prior_thread_project_id(session, email)
            match = match_project(
                email=email,
                candidates=candidates,
                prior_thread_project_id=prior,
                user_override=None,
            )
        await _insert_interpretation(session, email, match)
        if is_new and match.project_id is not None:
            await _emit_email_project_verbs(
                session,
                email=email,
                project_id=match.project_id,
                interpretation=_interpretation_from_match(email, match),
            )
        if is_new and should_ingest_attachments(match) and actor_id is not None:
            persisted = await session.get(ProjectEmail, email_id)
            interpretation = await session.get(ProjectEmailInterpretation, email_id)
            if persisted is not None and interpretation is not None:
                await _maybe_ingest_matched_attachments(
                    session,
                    email=persisted,
                    interpretation=interpretation,
                    actor_id=actor_id,
                    provider=provider,
                )
    return inserted


async def lookup_prior_thread_project_id(
    session: AsyncSession, email: ProjectEmail
) -> uuid.UUID | None:
    from app.email.project_matching import thread_key

    key = thread_key(email)
    if key.startswith("solo:"):
        return None
    stmt = (
        select(ProjectEmailInterpretation.project_id)
        .join(ProjectEmail, ProjectEmail.id == ProjectEmailInterpretation.email_id)
        .where(
            ProjectEmail.id != email.id,
            ProjectEmailInterpretation.project_id.is_not(None),
        )
    )
    if email.provider_thread_id:
        stmt = stmt.where(
            ProjectEmail.provider == email.provider,
            ProjectEmail.provider_thread_id == email.provider_thread_id,
        )
    else:
        message_ids = _referenced_message_ids(email)
        if not message_ids:
            return None
        stmt = stmt.where(ProjectEmail.internet_message_id.in_(message_ids))
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none()


def _candidate_from_project(project: Project) -> ProjectMatchCandidate:
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    taxonomy = metadata.get("taxonomy") if isinstance(metadata.get("taxonomy"), dict) else {}
    site = taxonomy.get("site_address") or metadata.get("site_address")
    client = taxonomy.get("client") or metadata.get("client")
    code = taxonomy.get("project_number") or taxonomy.get("code")
    domains: list[str] = []
    addresses: list[str] = []
    for obj in list_shared_project_objects(project, kind="consultant"):
        value = obj.value if isinstance(obj.value, dict) else {}
        domain = value.get("email_domain") or value.get("domain")
        if isinstance(domain, str) and domain.strip():
            domains.append(domain.strip())
        extra = value.get("email_domains")
        if isinstance(extra, list):
            domains.extend(str(item) for item in extra if item)
        addr = value.get("email") or value.get("email_address")
        if isinstance(addr, str) and "@" in addr:
            addresses.append(addr.strip())
    return ProjectMatchCandidate(
        project_id=project.id,
        slug=project.slug,
        title=project.title,
        code=str(code) if code else None,
        site_address=str(site) if site else None,
        client_name=str(client) if client else None,
        email_domains=tuple(domains),
        stored_addresses=tuple(addresses),
    )


def _email_from_message(
    message: RawProviderMessage, email_id: uuid.UUID
) -> ProjectEmail:
    return ProjectEmail(
        id=email_id,
        provider=message.provider,
        provider_message_id=message.provider_message_id,
        provider_thread_id=message.provider_thread_id,
        internet_message_id=message.internet_message_id,
        from_address=message.from_address,
        to_addresses=message.to_addresses,
        cc_addresses=message.cc_addresses,
        subject=message.subject,
        sent_at=message.sent_at,
        body_text=message.body_text,
        headers=message.headers,
        content_hash=email_content_hash(
            internet_message_id=message.internet_message_id,
            from_address=message.from_address,
            sent_at=message.sent_at,
            subject=message.subject,
            body_text=message.body_text,
        ),
        created_at=datetime.now(UTC),
    )


def _referenced_message_ids(email: ProjectEmail) -> tuple[str, ...]:
    headers = email.headers if isinstance(email.headers, dict) else {}
    values: list[str] = []
    for key, raw in headers.items():
        lowered = key.lower()
        if lowered in {"in-reply-to", "references"} and isinstance(raw, str):
            values.extend(raw.split())
    if email.internet_message_id:
        values.append(email.internet_message_id)
    return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))


async def _maybe_ingest_matched_attachments(
    session: AsyncSession,
    *,
    email: ProjectEmail,
    interpretation: ProjectEmailInterpretation,
    actor_id: uuid.UUID | None,
    provider: EmailProvider | None,
) -> None:
    match = ProjectMatch(
        project_id=interpretation.project_id,
        confidence=float(interpretation.match_confidence or 0),
        basis=interpretation.match_basis or "default",  # type: ignore[arg-type]
    )
    if not should_ingest_attachments(match):
        return
    if actor_id is None or interpretation.project_id is None:
        return
    project = await session.get(Project, interpretation.project_id)
    if project is None:
        return
    attachments = (
        await session.execute(
            select(ProjectEmailAttachment).where(
                ProjectEmailAttachment.email_id == email.id
            )
        )
    ).scalars().all()
    for attachment in attachments:
        if provider is None:
            continue
        content = await provider.get_attachment_bytes(
            email.provider_message_id, attachment.provider_attachment_id
        )
        await ingest_email_attachment(
            session,
            project=project,
            email_id=email.id,
            filename=attachment.filename,
            content=content,
            created_by_user_id=actor_id,
        )


async def _insert_interpretation(
    session: AsyncSession, email: ProjectEmail, match: ProjectMatch
) -> None:
    intel = _intelligence_payload(email)
    stmt = (
        pg_insert(ProjectEmailInterpretation)
        .values(
            email_id=email.id,
            project_id=match.project_id,
            match_confidence=Decimal(str(round(match.confidence, 3))),
            match_basis=match.basis,
            match_reviewed_by_user_id=None,
            message_category=intel["message_category"],
            actions=intel["actions"],
            updated_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["email_id"])
    )
    await session.execute(stmt)


def _intelligence_payload(email: ProjectEmail) -> dict[str, Any]:
    return {
        "message_category": classify_message_category(email),
        "actions": [item.model_dump() for item in detect_action_candidates(email)],
    }


def _interpretation_from_match(
    email: ProjectEmail, match: ProjectMatch
) -> ProjectEmailInterpretation:
    intel = _intelligence_payload(email)
    return ProjectEmailInterpretation(
        email_id=email.id,
        project_id=match.project_id,
        match_confidence=Decimal(str(round(match.confidence, 3))),
        match_basis=match.basis,
        message_category=intel["message_category"],
        actions=intel["actions"],
        updated_at=datetime.now(UTC),
    )


async def _persist_intelligence(
    session: AsyncSession,
    *,
    email: ProjectEmail,
    interpretation: ProjectEmailInterpretation,
) -> None:
    intel = _intelligence_payload(email)
    if not interpretation.message_category:
        interpretation.message_category = intel["message_category"]
    existing = interpretation.actions if isinstance(interpretation.actions, list) else []
    if not existing:
        interpretation.actions = intel["actions"]
        flag_modified(interpretation, "actions")


async def _emit_email_project_verbs(
    session: AsyncSession,
    *,
    email: ProjectEmail,
    project_id: uuid.UUID,
    interpretation: ProjectEmailInterpretation,
) -> None:
    subject = (email.subject or "email").strip() or "email"
    await record_project_verb(
        session,
        project_id=project_id,
        verb="email.received",
        reference_type="email",
        reference_id=email.id,
        message=f"Received {subject}",
        deduplication_key=verb_dedup_key(
            "email.received",
            reference_type="email",
            reference_id=email.id,
            extra=f"{email.provider}:{email.provider_message_id}",
        ),
        metadata={"subject_key": str(email.id)},
    )
    await record_project_verb(
        session,
        project_id=project_id,
        verb="email.linked",
        reference_type="email",
        reference_id=email.id,
        message="Linked email to project",
        deduplication_key=verb_dedup_key(
            "email.linked",
            reference_type="email",
            reference_id=email.id,
            extra=str(project_id),
        ),
        metadata={"subject_key": str(email.id)},
    )
    raw_actions = interpretation.actions if isinstance(interpretation.actions, list) else []
    if not raw_actions:
        raw_actions = _intelligence_payload(email)["actions"]
    for raw in raw_actions:
        action = (
            raw
            if isinstance(raw, EmailActionCandidate)
            else EmailActionCandidate.model_validate(raw)
        )
        await record_project_verb(
            session,
            project_id=project_id,
            verb="email.action_detected",
            reference_type="email",
            reference_id=email.id,
            message=_action_message(email, action),
            deduplication_key=verb_dedup_key(
                "email.action_detected",
                reference_type="email",
                reference_id=email.id,
                extra=action.type,
            ),
            metadata={
                "signal_type": action.type,
                "subject_key": str(email.id),
                "confidence": action.confidence,
            },
        )


def _action_message(email: ProjectEmail, action: EmailActionCandidate) -> str:
    if classify_message_category(email) == "rfi" or action.type == "reply_required":
        if "rfi" in f"{email.subject} {email.body_text}".lower() or "RFI" in (
            email.subject or ""
        ):
            return "RFI detected in thread"
    labels = {
        "reply_required": "Reply required in thread",
        "decision_required": "Decision required in thread",
        "commit_date": "Commitment date detected in thread",
        "cost_signal": "Cost signal detected in thread",
        "document_transmittal": "Transmittal detected in thread",
    }
    return labels[action.type]



async def _insert_raw_email(
    session: AsyncSession, message: RawProviderMessage
) -> uuid.UUID | None:
    email_id = uuid.uuid4()
    stmt = (
        pg_insert(ProjectEmail)
        .values(
            id=email_id,
            mailbox_account_id=None,
            provider=message.provider,
            provider_message_id=message.provider_message_id,
            provider_thread_id=message.provider_thread_id,
            internet_message_id=message.internet_message_id,
            from_address=message.from_address,
            to_addresses=message.to_addresses,
            cc_addresses=message.cc_addresses,
            subject=message.subject,
            sent_at=message.sent_at,
            body_text=message.body_text,
            headers=message.headers,
            raw_storage_key=None,
            content_hash=email_content_hash(
                internet_message_id=message.internet_message_id,
                from_address=message.from_address,
                sent_at=message.sent_at,
                subject=message.subject,
                body_text=message.body_text,
            ),
        )
        .on_conflict_do_nothing(
            index_elements=["provider", "provider_message_id"],
        )
        .returning(ProjectEmail.id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _existing_email_id(
    session: AsyncSession, message: RawProviderMessage
) -> uuid.UUID:
    result = await session.execute(
        select(ProjectEmail.id).where(
            ProjectEmail.provider == message.provider,
            ProjectEmail.provider_message_id == message.provider_message_id,
        )
    )
    return result.scalar_one()


async def _insert_attachment_refs(
    session: AsyncSession,
    email_id: uuid.UUID,
    message: RawProviderMessage,
) -> None:
    for attachment in message.attachments:
        stmt = (
            pg_insert(ProjectEmailAttachment)
            .values(
                id=uuid.uuid4(),
                email_id=email_id,
                provider_attachment_id=attachment.provider_attachment_id,
                filename=attachment.filename,
                content_type=attachment.content_type,
                size_bytes=attachment.size_bytes,
                content_hash=None,
                source_document_id=None,
            )
            .on_conflict_do_nothing(
                index_elements=["email_id", "provider_attachment_id"],
            )
        )
        await session.execute(stmt)


async def create_email_draft(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    to_addresses: Sequence[str],
    subject: str,
    body_text: str,
    cc_addresses: Sequence[str] | None = None,
    in_reply_to_email_id: uuid.UUID | None = None,
    provider: EmailProvider | None = None,
    references: dict | None = None,
) -> ProjectEmailDraft:
    """Insert a draft. Never calls provider.send_draft."""
    project = await session.get(Project, project_id)
    if project is None or project.owner_user_id != created_by_user_id:
        raise EmailNotFound(project_id)
    if in_reply_to_email_id is not None:
        await _require_project_email(
            session, project_id=project_id, email_id=in_reply_to_email_id
        )
    provider_draft_id = None
    if provider is not None:
        provider_draft_id = await provider.create_draft(
            ProviderDraft(
                to_addresses=list(to_addresses),
                cc_addresses=list(cc_addresses or ()),
                subject=subject,
                body_text=body_text,
                in_reply_to=str(in_reply_to_email_id)
                if in_reply_to_email_id is not None
                else None,
            )
        )
    draft = ProjectEmailDraft(
        id=uuid.uuid4(),
        project_id=project_id,
        created_by_user_id=created_by_user_id,
        in_reply_to_email_id=in_reply_to_email_id,
        to_addresses=list(to_addresses),
        cc_addresses=list(cc_addresses or ()),
        subject=subject,
        body_text=body_text,
        provider_draft_id=provider_draft_id,
        status="draft",
        references=dict(references or {}),
    )
    session.add(draft)
    await session.flush()
    return draft


async def reply_email_draft(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    email_id: uuid.UUID,
    body_text: str,
    to_addresses: Sequence[str] | None = None,
    cc_addresses: Sequence[str] | None = None,
    provider: EmailProvider | None = None,
) -> ProjectEmailDraft:
    email = await _require_project_email(
        session, project_id=project_id, email_id=email_id
    )
    subject = email.subject or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}" if subject else "Re:"
    recipients = list(to_addresses) if to_addresses else [email.from_address]
    return await create_email_draft(
        session,
        project_id=project_id,
        created_by_user_id=created_by_user_id,
        to_addresses=recipients,
        cc_addresses=cc_addresses,
        subject=subject,
        body_text=body_text,
        in_reply_to_email_id=email.id,
        provider=provider,
    )


async def forward_email_draft(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    email_id: uuid.UUID,
    to_addresses: Sequence[str],
    body_text: str = "",
    cc_addresses: Sequence[str] | None = None,
    provider: EmailProvider | None = None,
) -> ProjectEmailDraft:
    email = await _require_project_email(
        session, project_id=project_id, email_id=email_id
    )
    subject = email.subject or ""
    if not subject.lower().startswith("fwd:"):
        subject = f"Fwd: {subject}" if subject else "Fwd:"
    quoted = body_text or f"\n\n---------- Forwarded message ----------\n{email.body_text}"
    return await create_email_draft(
        session,
        project_id=project_id,
        created_by_user_id=created_by_user_id,
        to_addresses=to_addresses,
        cc_addresses=cc_addresses,
        subject=subject,
        body_text=quoted,
        in_reply_to_email_id=email.id,
        provider=provider,
    )


async def send_email_draft(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    provider: EmailProvider,
) -> ProjectEmailDraft:
    if actor_id is None:
        raise ValueError("actor_id is required to send a draft")
    project = await session.get(Project, project_id)
    if project is None or project.owner_user_id != actor_id:
        raise EmailNotFound(draft_id)
    draft = await session.get(
        ProjectEmailDraft, draft_id, with_for_update=True
    )
    if draft is None or draft.project_id != project_id:
        await session.rollback()
        raise EmailNotFound(draft_id)
    if draft.status != "draft":
        await session.rollback()
        raise EmailDraftConflict(f"cannot send draft in status {draft.status}")
    draft.status = "sending"
    draft.sent_by_user_id = actor_id
    await session.commit()
    await session.refresh(draft)
    try:
        if not draft.provider_draft_id:
            raise EmailDraftConflict("draft has no provider_draft_id")
        message_id = await provider.send_draft(
            draft.provider_draft_id, actor_id=actor_id
        )
    except EmailDraftConflict:
        draft.status = "send_failed"
        draft.send_error = "draft has no provider_draft_id"
        await session.commit()
        raise
    except Exception as exc:
        draft.status = "send_failed"
        draft.send_error = str(exc)
        await session.commit()
        raise
    draft.status = "sent"
    draft.sent_at = datetime.now(UTC)
    if message_id:
        draft.provider_message_id = str(message_id)
    await session.commit()
    await session.refresh(draft)
    return draft


async def _require_project_email(
    session: AsyncSession, *, project_id: uuid.UUID, email_id: uuid.UUID
) -> ProjectEmail:
    email = await session.get(ProjectEmail, email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if (
        email is None
        or interpretation is None
        or interpretation.project_id != project_id
    ):
        raise EmailNotFound(email_id)
    return email


def _email_view(
    email: ProjectEmail, interpretation: ProjectEmailInterpretation | None
) -> dict[str, Any]:
    return {
        "email_id": str(email.id),
        "project_id": None
        if interpretation is None or interpretation.project_id is None
        else str(interpretation.project_id),
        "provider": email.provider,
        "provider_message_id": email.provider_message_id,
        "provider_thread_id": email.provider_thread_id,
        "from_address": email.from_address,
        "to_addresses": list(email.to_addresses or []),
        "cc_addresses": list(email.cc_addresses or []),
        "subject": email.subject,
        "sent_at": None if email.sent_at is None else email.sent_at.isoformat(),
        "body_text": email.body_text,
        "message_category": None
        if interpretation is None
        else interpretation.message_category,
        "summary": None if interpretation is None else interpretation.summary,
        "actions": []
        if interpretation is None or not isinstance(interpretation.actions, list)
        else interpretation.actions,
    }


def email_draft_payload(draft: ProjectEmailDraft) -> dict[str, Any]:
    return {
        "id": str(draft.id),
        "project_id": str(draft.project_id),
        "status": draft.status,
        "to_addresses": list(draft.to_addresses or []),
        "cc_addresses": list(draft.cc_addresses or []),
        "subject": draft.subject,
        "body_text": draft.body_text,
        "in_reply_to_email_id": None
        if draft.in_reply_to_email_id is None
        else str(draft.in_reply_to_email_id),
        "provider_draft_id": draft.provider_draft_id,
        "provider_message_id": draft.provider_message_id,
        "send_error": draft.send_error,
        "sent_at": None if draft.sent_at is None else draft.sent_at.isoformat(),
        "sent_by_user_id": None
        if draft.sent_by_user_id is None
        else str(draft.sent_by_user_id),
        "references": dict(draft.references or {}),
    }


async def search_project_emails(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    query: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    stmt = (
        select(ProjectEmail, ProjectEmailInterpretation)
        .join(
            ProjectEmailInterpretation,
            ProjectEmailInterpretation.email_id == ProjectEmail.id,
        )
        .where(ProjectEmailInterpretation.project_id == project_id)
        .order_by(ProjectEmail.sent_at.desc(), ProjectEmail.created_at.desc())
        .limit(limit)
    )
    term = query.strip()
    if term:
        pattern = f"%{term}%"
        stmt = stmt.where(
            or_(
                ProjectEmail.subject.ilike(pattern),
                ProjectEmail.body_text.ilike(pattern),
                ProjectEmail.from_address.ilike(pattern),
            )
        )
    rows = (await session.execute(stmt)).all()
    return [_email_view(email, interpretation) for email, interpretation in rows]


async def list_project_correspondence(
    session: AsyncSession, *, project_id: uuid.UUID, limit: int = 50
) -> list[dict[str, Any]]:
    return await search_project_emails(
        session, project_id=project_id, query="", limit=limit
    )


async def read_email_thread(
    session: AsyncSession, *, project_id: uuid.UUID, email_id: uuid.UUID
) -> list[dict[str, Any]]:
    seed = await _require_project_email(
        session, project_id=project_id, email_id=email_id
    )
    stmt = (
        select(ProjectEmail, ProjectEmailInterpretation)
        .join(
            ProjectEmailInterpretation,
            ProjectEmailInterpretation.email_id == ProjectEmail.id,
        )
        .where(ProjectEmailInterpretation.project_id == project_id)
        .order_by(ProjectEmail.sent_at.asc(), ProjectEmail.created_at.asc())
    )
    if seed.provider_thread_id:
        stmt = stmt.where(
            ProjectEmail.provider == seed.provider,
            ProjectEmail.provider_thread_id == seed.provider_thread_id,
        )
    else:
        stmt = stmt.where(ProjectEmail.id == seed.id)
    rows = (await session.execute(stmt)).all()
    return [_email_view(email, interpretation) for email, interpretation in rows]


async def get_email_attachment(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> dict[str, Any]:
    attachment = await session.get(ProjectEmailAttachment, attachment_id)
    if attachment is None:
        raise EmailNotFound(attachment_id)
    await _require_project_email(
        session, project_id=project_id, email_id=attachment.email_id
    )
    return {
        "id": str(attachment.id),
        "email_id": str(attachment.email_id),
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "source_document_id": None
        if attachment.source_document_id is None
        else str(attachment.source_document_id),
    }


async def propose_email_action(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    email_id: uuid.UUID,
    action_type: str,
    excerpt: str,
    actor_id: uuid.UUID,
) -> dict[str, Any]:
    await _require_project_email(session, project_id=project_id, email_id=email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is None:
        raise EmailNotFound(email_id)
    candidate = {
        "type": action_type,
        "excerpt": excerpt[:280],
        "locator": "agent",
        "confidence": 0.0,
        "status": "candidate",
        "proposed_by_user_id": str(actor_id),
    }
    actions = list(interpretation.actions or [])
    actions.append(candidate)
    interpretation.actions = actions
    flag_modified(interpretation, "actions")
    return candidate


async def propose_project_decision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    title: str,
    body: str,
    email_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    candidate = {
        "kind": "proposed_decision",
        "title": title,
        "body": body,
        "status": "candidate",
        "proposed_by_user_id": str(actor_id),
        "email_id": None if email_id is None else str(email_id),
    }
    if email_id is None:
        return candidate
    await _require_project_email(session, project_id=project_id, email_id=email_id)
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is None:
        raise EmailNotFound(email_id)
    actions = list(interpretation.actions or [])
    actions.append(candidate)
    interpretation.actions = actions
    flag_modified(interpretation, "actions")
    return candidate
