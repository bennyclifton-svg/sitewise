from __future__ import annotations

import uuid
from typing import Any, Protocol


class TenderArtefactPublisher(Protocol):
    async def publish_draft(
        self,
        session: Any,
        *,
        project: Any,
        comparison_id: uuid.UUID,
        report_version: int,
        author_user_id: uuid.UUID,
        title: str,
        workspace_path: str,
        markdown: str,
    ) -> uuid.UUID: ...

    async def read_markdown(self, session: Any, *, draft_id: uuid.UUID) -> str | None: ...

    async def read_projection(
        self, session: Any, *, draft_id: uuid.UUID
    ) -> dict[str, Any] | None: ...

    async def publish_approved(
        self,
        session: Any,
        *,
        draft_id: uuid.UUID,
        comparison_id: uuid.UUID,
        report_version: int,
        approved_by: uuid.UUID,
        html_path: str,
        pdf_path: str,
    ) -> None: ...


class TenderArtefactPublisherNotConfigured(RuntimeError):
    pass


_publisher: TenderArtefactPublisher | None = None


def configure_tender_artefact_publisher(publisher: TenderArtefactPublisher) -> None:
    global _publisher
    _publisher = publisher


def tender_artefact_publisher() -> TenderArtefactPublisher:
    if _publisher is None:
        raise TenderArtefactPublisherNotConfigured(
            "Tender artefact publisher was not configured by application composition"
        )
    return _publisher
