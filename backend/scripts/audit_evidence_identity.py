"""Read-only audit for SourceDocument project ownership.

By default only aggregate counts are printed. Pass ``--show-identifiers`` to
include document IDs and paths when running in an approved environment.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory


@dataclass(frozen=True, slots=True)
class EvidenceIdentityAudit:
    project_evidence_rows: int
    platform_rows: int
    zero_owner_rows: int
    single_owner_rows: int
    ambiguous_owner_rows: int
    assigned_owner_mismatch_rows: int
    cross_project_duplicate_paths: int
    within_project_duplicate_paths: int
    shared_document_ids: int
    platform_owner_violations: int
    identifiers: list[dict[str, object]]


_AUDIT_SQL = text(
    """
    WITH owner_edges AS (
      SELECT source_document_id, project_id
      FROM workspace_files
      WHERE source_document_id IS NOT NULL
      UNION
      SELECT citation.document_id AS source_document_id, thread.project_id
      FROM message_citations AS citation
      JOIN chat_messages AS message ON message.id = citation.message_id
      JOIN chat_threads AS thread ON thread.id = message.thread_id
      WHERE thread.project_id IS NOT NULL
    ),
    ownership AS (
      SELECT
        document.id,
        document.relative_path,
        NULLIF(to_jsonb(document)->>'project_id', '')::uuid AS project_id,
        document.source_type,
        document.document_metadata,
        count(DISTINCT owner.project_id) AS owner_count,
        array_remove(array_agg(DISTINCT owner.project_id), NULL) AS owner_ids
      FROM source_documents AS document
      LEFT JOIN owner_edges AS owner ON owner.source_document_id = document.id
      GROUP BY document.id
    )
    SELECT * FROM ownership ORDER BY relative_path, id
    """
)


def _is_platform(row: object) -> bool:
    metadata = getattr(row, "document_metadata", None) or {}
    return metadata.get("knowledge_scope") == "platform"


async def audit_evidence_identity(
    session: AsyncSession, *, show_identifiers: bool = False
) -> EvidenceIdentityAudit:
    rows = list((await session.execute(_AUDIT_SQL)).all())
    project_rows = [row for row in rows if row.source_type == "project_evidence"]
    platform_rows = [row for row in rows if _is_platform(row)]
    path_projects: dict[str, set[object]] = {}
    path_owner_documents: dict[tuple[str, object], set[object]] = {}
    mismatched: list[object] = []
    for row in project_rows:
        owners = set(row.owner_ids or [])
        if row.project_id is not None and owners and row.project_id not in owners:
            mismatched.append(row)
        if row.project_id is not None:
            owners.add(row.project_id)
        path_projects.setdefault(row.relative_path, set()).update(owners)
        for owner_id in owners:
            path_owner_documents.setdefault((row.relative_path, owner_id), set()).add(row.id)

    ambiguous = [
        row
        for row in project_rows
        if int(row.owner_count) > 1 or row in mismatched
    ]
    identifiers = []
    if show_identifiers:
        identifiers = [
            {
                "document_id": str(row.id),
                "relative_path": row.relative_path,
                "project_id": str(row.project_id) if row.project_id else None,
                "owner_ids": [str(value) for value in row.owner_ids or []],
            }
            for row in project_rows
            if int(row.owner_count) != 1 or row in mismatched
        ]

    return EvidenceIdentityAudit(
        project_evidence_rows=len(project_rows),
        platform_rows=len(platform_rows),
        zero_owner_rows=sum(int(row.owner_count) == 0 for row in project_rows),
        single_owner_rows=sum(int(row.owner_count) == 1 for row in project_rows),
        ambiguous_owner_rows=len(ambiguous),
        assigned_owner_mismatch_rows=len(mismatched),
        cross_project_duplicate_paths=sum(len(owners) > 1 for owners in path_projects.values()),
        within_project_duplicate_paths=sum(
            len(document_ids) > 1 for document_ids in path_owner_documents.values()
        ),
        shared_document_ids=len(ambiguous),
        platform_owner_violations=sum(
            row.project_id is not None for row in platform_rows
        ),
        identifiers=identifiers,
    )


async def _run(show_identifiers: bool) -> None:
    factory = get_session_factory()
    async with factory() as session:
        before = session.info.get("audit_write_count", 0)
        result = await audit_evidence_identity(session, show_identifiers=show_identifiers)
        assert session.info.get("audit_write_count", 0) == before
        print(json.dumps(asdict(result), indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-identifiers", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(args.show_identifiers))


if __name__ == "__main__":
    main()
