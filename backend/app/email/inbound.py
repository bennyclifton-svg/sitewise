"""Resolve PROJECTCODE@in.sitewise.au and ingest inbound alias mail (Stage 22)."""

from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime
from email.utils import parseaddr
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.project import Project
from app.email import service as email_service
from app.email.alias_names import is_reserved_inbound_local_part
from app.email.project_matching import ProjectMatch
from app.email.schemas import RawProviderAttachment, RawProviderMessage
from app.inbox.service import InboxUploadItem, validate_upload_item
from app.logging import get_logger

logger = get_logger(__name__)

INBOUND_SIGNATURE_HEADER = "x-sitewise-inbound-signature"
INBOUND_EMAIL_PATH = "/internal/email/inbound"
_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


class InboundAliasUnresolved(LookupError):
    """No unique project for the inbound alias (404, never guess)."""


class InboundAttachmentPayload(BaseModel):
    filename: str
    content_base64: str
    content_type: str | None = None


class InboundEmailPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_address: str = Field(alias="from")
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str = ""
    sent_at: datetime | None = None
    body_text: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    attachments: list[InboundAttachmentPayload] = Field(default_factory=list)


def project_code_from_alias(address: str) -> str | None:
    _, parsed = parseaddr(address.strip())
    if "@" not in parsed:
        return None
    local, domain = parsed.rsplit("@", 1)
    if domain.lower() != settings.email_inbound_domain.lower():
        return None
    code = local.strip().lower()
    if not _SLUG_RE.fullmatch(code) or is_reserved_inbound_local_part(code):
        return None
    return code


async def project_for_inbound_alias(
    session: AsyncSession, *, address: str
) -> Project | None:
    code = project_code_from_alias(address)
    if code is None:
        return None
    projects = (
        await session.execute(
            select(Project).where(func.lower(Project.slug) == code)
        )
    ).scalars().all()
    if len(projects) == 1:
        return projects[0]
    if len(projects) > 1:
        logger.warning(
            "inbound_alias_slug_collision",
            slug=code,
            project_ids=[str(project.id) for project in projects],
        )
    return None


async def ingest_inbound_payload(
    session: AsyncSession, payload: dict[str, Any]
) -> dict[str, str]:
    parsed = InboundEmailPayload.model_validate(payload)
    project = await _unique_project_for_payload(session, parsed)
    decoded = _decoded_attachments(parsed)
    message = _raw_message(parsed, decoded)
    email_id = await email_service._insert_raw_email(session, message)
    if email_id is None:
        email_id = await email_service._existing_email_id(session, message)
        return {"email_id": str(email_id)}
    await email_service._insert_attachment_refs(session, email_id, message)
    match = ProjectMatch(project_id=project.id, confidence=1.0, basis="alias")
    email = email_service._email_from_message(message, email_id)
    await email_service._insert_interpretation(session, email, match)
    await email_service._emit_email_project_verbs(
        session,
        email=email,
        project_id=project.id,
        interpretation=email_service._interpretation_from_match(email, match),
    )
    for filename, content in decoded:
        await email_service.ingest_email_attachment(
            session,
            project=project,
            email_id=email_id,
            filename=filename,
            content=content,
            created_by_user_id=project.owner_user_id,
        )
    return {"email_id": str(email_id)}


async def _unique_project_for_payload(
    session: AsyncSession, payload: InboundEmailPayload
) -> Project:
    found: Project | None = None
    for address in [*payload.to, *payload.cc, *payload.bcc]:
        project = await project_for_inbound_alias(session, address=address)
        if project is None:
            continue
        if found is not None and project.id != found.id:
            logger.warning(
                "inbound_alias_multiple_projects",
                first_project_id=str(found.id),
                second_project_id=str(project.id),
            )
            raise InboundAliasUnresolved(address)
        found = project
    if found is None:
        raise InboundAliasUnresolved()
    return found


def _decoded_attachments(
    payload: InboundEmailPayload,
) -> list[tuple[str, bytes]]:
    decoded: list[tuple[str, bytes]] = []
    for attachment in payload.attachments:
        try:
            content = base64.b64decode(attachment.content_base64, validate=True)
        except binascii.Error as exc:
            raise ValueError(
                f"invalid attachment encoding: {attachment.filename}"
            ) from exc
        validate_upload_item(
            InboxUploadItem(filename=attachment.filename, content=content)
        )
        decoded.append((attachment.filename, content))
    return decoded


def _raw_message(
    payload: InboundEmailPayload,
    decoded: list[tuple[str, bytes]],
) -> RawProviderMessage:
    headers = {key.lower(): value for key, value in payload.headers.items()}
    if payload.bcc:
        headers["x-original-bcc"] = ", ".join(payload.bcc)
    internet_message_id = headers.get("message-id")
    provider_message_id = internet_message_id or email_service.email_content_hash(
        internet_message_id=internet_message_id,
        from_address=payload.from_address,
        sent_at=payload.sent_at,
        subject=payload.subject,
        body_text=payload.body_text,
    )
    attachments = [
        RawProviderAttachment(
            provider_attachment_id=f"inbound-{index}",
            filename=filename,
            content_type=_content_type(payload.attachments[index]),
            size_bytes=len(content),
        )
        for index, (filename, content) in enumerate(decoded)
    ]
    return RawProviderMessage(
        provider="inbound_alias",
        provider_message_id=provider_message_id,
        internet_message_id=internet_message_id,
        from_address=payload.from_address,
        to_addresses=list(payload.to),
        cc_addresses=list(payload.cc),
        subject=payload.subject,
        sent_at=payload.sent_at,
        body_text=payload.body_text,
        headers=headers,
        attachments=attachments,
    )


def _content_type(attachment: InboundAttachmentPayload) -> str:
    return attachment.content_type or "application/octet-stream"


def inbound_request_exceeds_limit(*, content_length: str | None, body_len: int) -> bool:
    max_bytes = settings.email_inbound_max_body_bytes
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                return True
        except ValueError:
            return True
    return body_len > max_bytes
