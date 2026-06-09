import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.database.source_document import SourceDocument
from app.retrieval.schemas import SourcePassage
from app.retrieval.schemas import RetrievalFilters
from app.retrieval.queries import apply_document_filters


class DrawingRegisterRow(BaseModel):
    document_id: uuid.UUID
    filename: str
    relative_path: str
    project: str
    phase: str | None
    drawing_number: str | None
    revision: str | None
    title: str | None


def _metadata_text(metadata: dict | None, key: str) -> str | None:
    if not metadata:
        return None
    value = metadata.get(key)
    return value if isinstance(value, str) and value.strip() else None


async def list_drawings(
    session: AsyncSession,
    *,
    filters: RetrievalFilters | None = None,
) -> list[DrawingRegisterRow]:
    stmt = select(
        SourceDocument.id,
        SourceDocument.filename,
        SourceDocument.relative_path,
        SourceDocument.project,
        SourceDocument.phase,
        SourceDocument.document_metadata,
    ).where(SourceDocument.document_class == "drawing")
    stmt = apply_document_filters(stmt, filters)
    stmt = stmt.order_by(
        SourceDocument.project.asc(),
        SourceDocument.relative_path.asc(),
    )

    result = await session.execute(stmt)
    rows: list[DrawingRegisterRow] = []
    for row in result.all():
        metadata = row.document_metadata if isinstance(row.document_metadata, dict) else {}
        rows.append(
            DrawingRegisterRow(
                document_id=row.id,
                filename=row.filename,
                relative_path=row.relative_path,
                project=row.project,
                phase=row.phase,
                drawing_number=_metadata_text(metadata, "drawing_number"),
                revision=_metadata_text(metadata, "revision"),
                title=_metadata_text(metadata, "title"),
            )
        )
    return rows


def drawing_rows_to_passages(rows: list[DrawingRegisterRow]) -> list[SourcePassage]:
    passages: list[SourcePassage] = []
    for row in rows:
        label = row.drawing_number or row.filename
        passages.append(
            SourcePassage(
                chunk_id=row.document_id,
                document_id=row.document_id,
                chunk_index=0,
                content=(
                    f"Drawing register entry: {label}. "
                    f"Revision: {row.revision or 'unknown'}. "
                    f"Title: {row.title or row.filename}. "
                    f"Path: {row.relative_path}."
                ),
                page_or_section=row.revision,
                project=row.project,
                phase=row.phase,
                source_type="project_evidence",
                document_class="drawing",
                filename=row.filename,
                relative_path=row.relative_path,
                document_metadata={
                    "drawing_number": row.drawing_number,
                    "revision": row.revision,
                    "title": row.title,
                },
                chunk_metadata={"drawing_register": True},
                score=1.0,
                neighbours=[],
            )
        )
    return passages


def build_drawing_register_answer(rows: list[DrawingRegisterRow]) -> GroundedAnswer:
    if not rows:
        return GroundedAnswer(
            answer="No drawings are indexed in the document register yet.",
            evidence_sufficient=False,
        )

    lines = ["These drawings are indexed in the Clerk document register:", ""]
    citations: list[Citation] = []
    for row in rows:
        number = row.drawing_number or row.filename
        revision = row.revision or "—"
        title = row.title or row.filename
        lines.append(
            f"- {number} | rev {revision} | {title} | `{row.relative_path}`"
        )
        citations.append(
            Citation(
                chunk_id=row.document_id,
                document_id=row.document_id,
                excerpt=f"Drawing register entry: {number}",
                filename=row.filename,
                project=row.project,
                phase=row.phase,
                source_type="project_evidence",
                page_or_section=row.revision,
                label=EvidenceLabel.FACT,
            )
        )

    return GroundedAnswer(
        answer="\n".join(lines),
        citations=citations,
        evidence_sufficient=True,
    )
