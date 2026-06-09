import uuid

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.retrieval.schemas import SourcePassage


class CorpusProjectSummary(BaseModel):
    project: str
    phase: str
    source_type: str | None
    document_count: int
    sample_chunk_id: uuid.UUID
    sample_document_id: uuid.UUID
    sample_filename: str
    sample_relative_path: str


async def list_corpus_projects(session: AsyncSession) -> list[CorpusProjectSummary]:
    counts = (
        select(
            SourceDocument.project,
            func.count(SourceDocument.id).label("document_count"),
        )
        .group_by(SourceDocument.project)
        .subquery()
    )

    ranked = (
        select(
            SourceDocument.project,
            SourceDocument.phase,
            SourceDocument.source_type,
            SourceDocument.id.label("document_id"),
            SourceDocument.filename,
            SourceDocument.relative_path,
            func.row_number()
            .over(
                partition_by=SourceDocument.project,
                order_by=(SourceDocument.created_at.asc(), SourceDocument.relative_path.asc()),
            )
            .label("row_num"),
        )
        .subquery()
    )

    stmt = (
        select(
            ranked.c.project,
            ranked.c.phase,
            ranked.c.source_type,
            counts.c.document_count,
            ranked.c.document_id.label("chunk_id"),
            ranked.c.document_id,
            ranked.c.filename,
            ranked.c.relative_path,
        )
        .join(counts, counts.c.project == ranked.c.project)
        .where(ranked.c.row_num == 1)
        .order_by(ranked.c.project.asc())
    )

    result = await session.execute(stmt)
    return [
        CorpusProjectSummary(
            project=row.project,
            phase=row.phase,
            source_type=row.source_type,
            document_count=row.document_count,
            sample_chunk_id=row.chunk_id,
            sample_document_id=row.document_id,
            sample_filename=row.filename,
            sample_relative_path=row.relative_path,
        )
        for row in result.all()
    ]


def catalog_to_passages(catalog: list[CorpusProjectSummary]) -> list[SourcePassage]:
    passages: list[SourcePassage] = []
    for entry in catalog:
        passages.append(
            SourcePassage(
                chunk_id=entry.sample_chunk_id,
                document_id=entry.sample_document_id,
                chunk_index=0,
                content=(
                    f"Corpus project: {entry.project}. "
                    f"Phase: {entry.phase}. "
                    f"Source type: {entry.source_type or 'unknown'}. "
                    f"Documents indexed: {entry.document_count}. "
                    f"Example file: {entry.sample_relative_path}."
                ),
                page_or_section=None,
                project=entry.project,
                phase=entry.phase,
                source_type=entry.source_type,
                document_class="corpus_catalog",
                filename=entry.sample_filename,
                relative_path=entry.sample_relative_path,
                document_metadata={"corpus_catalog": True, "document_count": entry.document_count},
                chunk_metadata={"corpus_catalog": True},
                score=1.0,
            )
        )
    return passages


def format_catalog_for_prompt(catalog: list[CorpusProjectSummary]) -> str:
    if not catalog:
        return "Corpus catalog: no projects are indexed yet."

    lines = ["Corpus catalog (authoritative list of indexed projects):"]
    for entry in catalog:
        lines.append(
            f"- {entry.project} | phase={entry.phase} | source_type={entry.source_type} "
            f"| documents={entry.document_count} | sample_chunk_id={entry.sample_chunk_id} "
            f"| sample_path={entry.sample_relative_path}"
        )
    return "\n".join(lines)


def build_catalog_answer(catalog: list[CorpusProjectSummary]):
    from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer

    if not catalog:
        return GroundedAnswer(
            answer=(
                "Hello. I'm Clerk. There are no projects indexed in the corpus yet."
            ),
            evidence_sufficient=False,
        )

    lines = [
        "Hello. I'm Clerk. I currently have indexed evidence for these corpus projects:",
        "",
    ]
    citations: list[Citation] = []
    for entry in catalog:
        lines.append(
            f"- {entry.project} ({entry.phase}, {entry.source_type or 'unknown'}) "
            f"— {entry.document_count} documents"
        )
        citations.append(
            Citation(
                chunk_id=entry.sample_chunk_id,
                document_id=entry.sample_document_id,
                excerpt=f"Corpus project: {entry.project}",
                filename=entry.sample_filename,
                project=entry.project,
                phase=entry.phase,
                source_type=entry.source_type,
                label=EvidenceLabel.FACT,
            )
        )

    return GroundedAnswer(
        answer="\n".join(lines),
        citations=citations,
        evidence_sufficient=True,
    )
