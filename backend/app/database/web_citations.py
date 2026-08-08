from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.message_web_citation import MessageWebCitation


def _required_text(source: Mapping[str, Any], field: str) -> str:
    value = source.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"web citation is missing {field}")
    return value.strip()


def _optional_text(source: Mapping[str, Any], field: str) -> str | None:
    value = source.get(field)
    return value.strip() if isinstance(value, str) and value.strip() else None


async def persist_message_web_citations(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    turn_id: uuid.UUID,
    message_id: uuid.UUID,
    sources: Sequence[Mapping[str, Any]],
) -> None:
    for source in sources:
        retrieved_at = datetime.fromisoformat(_required_text(source, "retrieved_at"))
        session.add(
            MessageWebCitation(
                project_id=project_id,
                turn_id=turn_id,
                message_id=message_id,
                url=_required_text(source, "url"),
                title=_required_text(source, "title"),
                publisher=_optional_text(source, "publisher"),
                jurisdiction=_optional_text(source, "jurisdiction"),
                authority_class=_required_text(source, "authority_class"),
                source_type=_required_text(source, "source_type"),
                version_status=_required_text(source, "version_status"),
                effective_date=_optional_text(source, "effective_date"),
                section=_optional_text(source, "section"),
                excerpt=_optional_text(source, "excerpt"),
                content_hash=_required_text(source, "content_hash"),
                retrieved_at=retrieved_at,
                citation_metadata={"retrieved_from": "official_web"},
            )
        )
