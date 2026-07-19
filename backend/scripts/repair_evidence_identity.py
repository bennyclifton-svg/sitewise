"""Split legacy SourceDocuments shared by more than one project.

The command is dry-run by default. ``--apply`` performs an idempotent repair in
one transaction and refuses to delete or quarantine evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from sqlalchemy import select, union

from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.document_chunk import DocumentChunk
from app.database.message_citation import MessageCitation
from app.database.project import Project
from app.database.session import get_session_factory
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from ingest.ids import chunk_id, document_id


async def ambiguous_documents(session) -> list[tuple[uuid.UUID, list[uuid.UUID]]]:
    owner_edges = union(
        select(
            WorkspaceFile.source_document_id.label("source_document_id"),
            WorkspaceFile.project_id.label("project_id"),
        ).where(WorkspaceFile.source_document_id.is_not(None)),
        select(
            MessageCitation.document_id.label("source_document_id"),
            ChatThread.project_id.label("project_id"),
        )
        .join(ChatMessage, MessageCitation.message_id == ChatMessage.id)
        .join(ChatThread, ChatMessage.thread_id == ChatThread.id)
        .where(ChatThread.project_id.is_not(None)),
    ).subquery()
    rows = await session.execute(
        select(owner_edges.c.source_document_id, owner_edges.c.project_id)
        .join(SourceDocument, owner_edges.c.source_document_id == SourceDocument.id)
        .where(SourceDocument.source_type == "project_evidence")
        .order_by(owner_edges.c.source_document_id, owner_edges.c.project_id)
    )
    owners: dict[uuid.UUID, set[uuid.UUID]] = {}
    for source_document_id, project_id in rows.all():
        owners.setdefault(source_document_id, set()).add(project_id)
    return [
        (source_document_id, sorted(project_ids, key=str))
        for source_document_id, project_ids in owners.items()
        if len(project_ids) > 1
    ]


async def _citation_rows(session, document_id_value: uuid.UUID, project_id: uuid.UUID):
    result = await session.execute(
        select(MessageCitation)
        .join(ChatMessage, MessageCitation.message_id == ChatMessage.id)
        .join(ChatThread, ChatMessage.thread_id == ChatThread.id)
        .where(
            MessageCitation.document_id == document_id_value,
            ChatThread.project_id == project_id,
        )
    )
    return list(result.scalars().all())


async def _project_slug(session, project_id: uuid.UUID) -> str:
    """Read only columns available before the Stage 2 project migrations."""
    slug = await session.scalar(select(Project.slug).where(Project.id == project_id))
    if slug is None:
        raise RuntimeError(f"owning project does not exist: {project_id}")
    return slug


async def repair_evidence_identity(session, *, apply: bool) -> dict[str, int]:
    ambiguous = await ambiguous_documents(session)
    summary = {
        "shared_documents": len(ambiguous),
        "project_copies": sum(len(owners) - 1 for _, owners in ambiguous),
        "workspace_files_repointed": 0,
        "citations_repointed": 0,
    }
    if not apply:
        return summary

    for source_document_id, owners in ambiguous:
        original = await session.get(SourceDocument, source_document_id, with_for_update=True)
        if original is None:
            continue
        retained_project_slug = await _project_slug(session, owners[0])
        original.project_id = owners[0]
        original.project = retained_project_slug
        chunks = list(
            (
                await session.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.document_id == source_document_id
                    )
                )
            )
            .scalars()
            .all()
        )

        for owner_id in owners[1:]:
            owner_project_slug = await _project_slug(session, owner_id)
            existing = await session.scalar(
                select(SourceDocument).where(
                    SourceDocument.project_id == owner_id,
                    SourceDocument.relative_path == original.relative_path,
                )
            )
            target = existing
            if target is not None and (
                target.content_hash != original.content_hash
                or target.normalized_content != original.normalized_content
            ):
                raise RuntimeError(
                    "existing project document differs from shared historical evidence: "
                    f"project={owner_id} path={original.relative_path}"
                )
            if target is None:
                target = SourceDocument(
                    id=document_id(original.relative_path, project_id=owner_id),
                    project_id=owner_id,
                    project=owner_project_slug,
                    phase=original.phase,
                    document_type=original.document_type,
                    document_class=original.document_class,
                    ingest_mode=original.ingest_mode,
                    document_metadata=dict(original.document_metadata or {}),
                    content_hash=original.content_hash,
                    source_type=original.source_type,
                    filename=original.filename,
                    relative_path=original.relative_path,
                    normalized_content=original.normalized_content,
                )
                session.add(target)
                await session.flush()
                for source_chunk in chunks:
                    session.add(
                        DocumentChunk(
                            id=chunk_id(target.id, source_chunk.chunk_index),
                            document_id=target.id,
                            chunk_index=source_chunk.chunk_index,
                            page_or_section=source_chunk.page_or_section,
                            content=source_chunk.content,
                            embedding=source_chunk.embedding,
                            token_count=source_chunk.token_count,
                            chunk_metadata=dict(source_chunk.chunk_metadata or {}),
                        )
                    )
                await session.flush()

            workspace_files = list(
                (
                    await session.execute(
                        select(WorkspaceFile).where(
                            WorkspaceFile.source_document_id == source_document_id,
                            WorkspaceFile.project_id == owner_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for workspace_file in workspace_files:
                workspace_file.source_document_id = target.id
            summary["workspace_files_repointed"] += len(workspace_files)

            target_chunks = {
                row.chunk_index: row.id
                for row in (
                    (
                        await session.execute(
                            select(DocumentChunk).where(DocumentChunk.document_id == target.id)
                        )
                    )
                    .scalars()
                    .all()
                )
            }
            source_chunk_indexes = {row.id: row.chunk_index for row in chunks}
            citations = await _citation_rows(session, source_document_id, owner_id)
            for citation in citations:
                citation.document_id = target.id
                index = source_chunk_indexes.get(citation.chunk_id)
                if citation.chunk_id is not None:
                    if index is None or index not in target_chunks:
                        raise RuntimeError(
                            "cannot preserve historical citation chunk mapping: "
                            f"citation={citation.id} project={owner_id}"
                        )
                    citation.chunk_id = target_chunks[index]
            summary["citations_repointed"] += len(citations)

    await session.flush()
    return summary


async def _run(apply: bool) -> None:
    async with get_session_factory()() as session:
        result = await repair_evidence_identity(session, apply=apply)
        if apply:
            await session.commit()
        else:
            await session.rollback()
        print(json.dumps({"mode": "apply" if apply else "dry-run", **result}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(args.apply))


if __name__ == "__main__":
    main()
