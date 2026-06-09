import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.database.source_document import SourceDocument
from app.retrieval.schemas import SourcePassage


class PlatformDocumentRow(BaseModel):
    document_id: uuid.UUID
    filename: str
    relative_path: str
    project: str
    phase: str | None
    source_type: str | None
    document_class: str
    knowledge_kind: str | None


async def list_platform_documents(
    session: AsyncSession,
    *,
    knowledge_kind: str | None = None,
) -> list[PlatformDocumentRow]:
    kind_expr = SourceDocument.document_metadata["sitewise_knowledge_kind"].astext
    scope_expr = SourceDocument.document_metadata["knowledge_scope"].astext
    stmt = (
        select(
            SourceDocument.id,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.project,
            SourceDocument.phase,
            SourceDocument.source_type,
            SourceDocument.document_class,
            kind_expr.label("knowledge_kind"),
        )
        .where(scope_expr == "platform")
        .order_by(SourceDocument.relative_path.asc())
    )
    if knowledge_kind is not None:
        stmt = stmt.where(kind_expr == knowledge_kind)

    result = await session.execute(stmt)
    return [
        PlatformDocumentRow(
            document_id=row.id,
            filename=row.filename,
            relative_path=row.relative_path,
            project=row.project,
            phase=row.phase,
            source_type=row.source_type,
            document_class=row.document_class,
            knowledge_kind=row.knowledge_kind,
        )
        for row in result.all()
    ]


async def list_seed_documents(session: AsyncSession) -> list[PlatformDocumentRow]:
    return await list_platform_documents(session, knowledge_kind="seed")


def platform_rows_to_passages(rows: list[PlatformDocumentRow]) -> list[SourcePassage]:
    passages: list[SourcePassage] = []
    for row in rows:
        passages.append(
            SourcePassage(
                chunk_id=row.document_id,
                document_id=row.document_id,
                chunk_index=0,
                content=(
                    f"Indexed platform document: {row.relative_path}. "
                    f"Kind: {row.knowledge_kind or row.document_class}."
                ),
                page_or_section=None,
                project=row.project,
                phase=row.phase,
                source_type=row.source_type,
                document_class=row.document_class,
                filename=row.filename,
                relative_path=row.relative_path,
                document_metadata={
                    "knowledge_scope": "platform",
                    "sitewise_knowledge_kind": row.knowledge_kind,
                },
                chunk_metadata={"platform_inventory": True},
                score=1.0,
            )
        )
    return passages


def build_platform_inventory_answer(
    rows: list[PlatformDocumentRow],
    *,
    title: str,
    empty_message: str,
) -> GroundedAnswer:
    if not rows:
        return GroundedAnswer(
            answer=empty_message,
            evidence_sufficient=False,
        )

    lines = [title, ""]
    citations: list[Citation] = []
    for row in rows:
        kind = row.knowledge_kind or row.document_class
        lines.append(f"- `{row.relative_path}` ({kind})")
        citations.append(
            Citation(
                chunk_id=row.document_id,
                document_id=row.document_id,
                excerpt=f"Indexed platform document: {row.relative_path}",
                filename=row.filename,
                project=row.project,
                phase=row.phase,
                source_type=row.source_type,
                label=EvidenceLabel.FACT,
            )
        )

    return GroundedAnswer(
        answer="\n".join(lines),
        citations=citations,
        evidence_sufficient=True,
    )


def build_seed_inventory_answer(rows: list[PlatformDocumentRow]) -> GroundedAnswer:
    return build_platform_inventory_answer(
        rows,
        title="These SiteWise seed knowledge files are indexed in Clerk:",
        empty_message=(
            "No seed knowledge files are indexed yet. "
            "Ingest the `seed/` folder to populate platform knowledge."
        ),
    )


def build_platform_knowledge_inventory_answer(
    rows: list[PlatformDocumentRow],
) -> GroundedAnswer:
    return build_platform_inventory_answer(
        rows,
        title="These SiteWise platform knowledge documents are indexed in Clerk:",
        empty_message="No SiteWise platform knowledge documents are indexed yet.",
    )
