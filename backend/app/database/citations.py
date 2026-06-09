import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.outputs import GroundedAnswer
from app.database.message_citation import MessageCitation


async def persist_message_citations(
    session: AsyncSession,
    *,
    message_id: uuid.UUID,
    answer: GroundedAnswer,
) -> None:
    for citation in answer.citations:
        session.add(
            MessageCitation(
                message_id=message_id,
                chunk_id=citation.chunk_id,
                document_id=citation.document_id,
                excerpt=citation.excerpt,
                citation_metadata={
                    "filename": citation.filename,
                    "project": citation.project,
                    "phase": citation.phase,
                    "source_type": citation.source_type,
                    "page_or_section": citation.page_or_section,
                    "label": citation.label.value,
                },
            )
        )


def citations_for_message_data(answer: GroundedAnswer) -> list[dict]:
    return [
        {
            "chunkId": str(citation.chunk_id),
            "documentId": str(citation.document_id),
            "sourceId": str(citation.chunk_id),
            "title": citation.filename,
            "project": citation.project,
            "phase": citation.phase,
            "sourceType": citation.source_type,
            "pageOrSection": citation.page_or_section,
            "label": citation.label.value,
            "excerpt": citation.excerpt,
        }
        for citation in answer.citations
    ]
