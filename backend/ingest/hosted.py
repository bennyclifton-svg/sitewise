from pathlib import Path
import tempfile
import uuid

from ingest.classify import classify_entry
from ingest.pipeline import ingest_plan
from ingest.router import build_ingest_plan
from ingest.types import ManifestEntry, ProjectContext


def ingest_hosted_file(
    *,
    content: bytes,
    workspace_path: str,
    project_slug: str,
    project_phase: str,
    filename: str,
    extension: str,
    skip_if_unchanged: bool = True,
) -> bool:
    suffix = extension if extension.startswith(".") else f".{extension}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        entry = ManifestEntry(
            absolute_path=temp_path,
            relative_path=workspace_path,
            project=project_slug,
            filename=filename,
            extension=extension.lower(),
            size_bytes=len(content),
        )
        context = ProjectContext(
            project=project_slug,
            phase=project_phase,
            source_type="project_evidence",
        )
        classification = classify_entry(entry)
        plan = build_ingest_plan(entry, context, classification)
        return ingest_plan(plan, skip_if_unchanged=skip_if_unchanged)
    finally:
        temp_path.unlink(missing_ok=True)


def source_document_id_for_path(workspace_path: str) -> uuid.UUID | None:
    from sqlalchemy import select

    from app.database.source_document import SourceDocument
    from ingest.db import get_sync_session_factory
    from ingest.ids import document_id

    doc_id = document_id(workspace_path)
    factory = get_sync_session_factory()
    with factory() as session:
        existing = session.scalar(select(SourceDocument.id).where(SourceDocument.id == doc_id))
        return existing
